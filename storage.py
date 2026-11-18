"""Lưu / đọc CSV, JSON, SQLite + gộp dữ liệu qua nhiều lần chạy."""
import csv
import json
import logging
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime

import config
from models import RateRecord, FIELD_NAMES

log = logging.getLogger("storage")
_OPT = ("buy_cash", "buy_transfer", "sell", "spread")


def _num(x):
    return None if x in (None, "", "None") else float(x)


def _from_row(d):
    d = dict(d)
    for k in _OPT:
        d[k] = _num(d.get(k))
    d["mid"] = float(d["mid"])
    d["is_major"] = str(d["is_major"]).lower() in ("true", "1")
    return RateRecord(**d)


# ---------- CSV ----------
def save_csv(records, path=config.CSV_PATH):
    config.ensure_dirs()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        w.writeheader()
        w.writerows(r.to_dict() for r in records)


def _read_csv(path):
    """Trả (records, ok). ok=False nếu file hỏng hoặc có dòng bị bỏ qua."""
    out, ok = [], True
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, strict=True)
            if reader.fieldnames != FIELD_NAMES:
                if reader.fieldnames is None:
                    log.warning("CSV rỗng: %s", path)
                    return [], True
                raise csv.Error("header không khớp cấu trúc RateRecord")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    log.warning("Bỏ qua dòng CSV thiếu/thừa cột: %s", row)
                    ok = False
                    continue
                try:
                    out.append(_from_row(row))
                except (ValueError, KeyError, TypeError) as e:
                    log.warning("Bỏ qua dòng CSV lỗi: %s (%s)", row, e)
                    ok = False
    except FileNotFoundError:
        log.warning("Không tìm thấy %s - hãy thu thập dữ liệu trước.", path)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        log.error("Không đọc được CSV %s: %s", path, e)
        return [], False
    return out, ok


def load_csv(path=config.CSV_PATH):
    return _read_csv(path)[0]


# ---------- JSON ----------
def save_json(records, path=config.JSON_PATH):
    config.ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in records], f, ensure_ascii=False, indent=2)


def load_json(path=config.JSON_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        log.warning("Không tìm thấy %s - hãy thu thập dữ liệu trước.", path)
        return []
    except json.JSONDecodeError as e:
        log.error("File JSON bị hỏng: %s", e)
        return []
    if not isinstance(data, list):
        log.error("JSON phải là danh sách bản ghi.")
        return []
    out = []
    for d in data:
        try:
            out.append(_from_row(d))
        except (ValueError, KeyError, TypeError):
            log.warning("Bỏ qua bản ghi JSON sai định dạng: %s", d)
    return out


# ---------- SQLite ----------
_DDL = """CREATE TABLE IF NOT EXISTS rates (
    source TEXT, date TEXT, fetched_at TEXT, base_ccy TEXT, currency_name TEXT,
    quote_ccy TEXT, buy_cash REAL, buy_transfer REAL, sell REAL, mid REAL,
    spread REAL, is_major INTEGER, PRIMARY KEY (source, date, base_ccy))"""


def save_sqlite(records, path=config.DB_PATH):
    config.ensure_dirs()
    sql = (f"INSERT OR REPLACE INTO rates ({','.join(FIELD_NAMES)}) "
           f"VALUES ({','.join(':' + n for n in FIELD_NAMES)})")
    with closing(sqlite3.connect(path)) as con:
        con.execute(_DDL)
        con.executemany(sql, [r.to_dict() for r in records])
        con.commit()


def load_sqlite(path=config.DB_PATH):
    if not path.exists():
        log.warning("Không tìm thấy %s", path)
        return []
    with closing(sqlite3.connect(path)) as con:
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("SELECT * FROM rates").fetchall()
        except sqlite3.Error as e:
            log.error("Lỗi đọc SQLite: %s", e)
            return []
    return [_from_row(dict(r)) for r in rows]


def sql_summary(path=config.DB_PATH):
    """Ví dụ truy vấn SQL: thống kê theo nguồn và ngoại tệ."""
    if not path.exists():
        return []
    with closing(sqlite3.connect(path)) as con:
        return con.execute(
            "SELECT source, base_ccy, COUNT(*), ROUND(AVG(mid), 4), MIN(date), MAX(date) "
            "FROM rates GROUP BY source, base_ccy ORDER BY source, base_ccy").fetchall()


# ---------- Tiện ích ----------
def load(fmt="csv"):
    return {"csv": load_csv, "json": load_json, "sqlite": load_sqlite}[fmt]()


def _backup(path):
    """Sao lưu file hỏng trước khi bị ghi đè để không mất dữ liệu."""
    bak = path.with_name(f"{path.stem}.broken_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
    shutil.copy2(path, bak)
    log.warning("CSV lỗi, đã sao lưu bản gốc sang %s", bak.name)


def _load_history():
    """Lịch sử cũ = SQLite ∪ CSV. SQLite không bao giờ bị xóa dòng nên là nguồn dự phòng
    khi CSV bị hỏng (vd mở bằng Excel rồi lưu lại làm đổi header)."""
    csv_path = config.CSV_PATH
    csv_recs, csv_ok = _read_csv(csv_path)
    if not csv_ok and csv_path.exists():
        _backup(csv_path)
    try:
        db_recs = load_sqlite(config.DB_PATH)
    except (sqlite3.Error, ValueError, KeyError, TypeError) as e:
        log.error("Không đọc được SQLite để gộp: %s", e)
        db_recs = []
    merged = {r.key: r for r in db_recs}
    merged.update({r.key: r for r in csv_recs})
    return merged


def merge_and_save(new_records):
    """Gộp với dữ liệu cũ (chạy nhiều ngày -> có lịch sử), bỏ trùng, lưu 3 định dạng."""
    merged = _load_history()
    for r in new_records:
        merged[r.key] = r
    allr = sorted(merged.values(), key=lambda r: (r.source, r.date, r.base_ccy))
    save_csv(allr, config.CSV_PATH)
    save_json(allr, config.JSON_PATH)
    save_sqlite(allr, config.DB_PATH)
    return allr
