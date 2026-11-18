"""Làm sạch + kiểm tra hợp lệ + chuyển sang RateRecord + báo cáo làm sạch."""
import logging
import math
import re
from dataclasses import dataclass, asdict
from datetime import datetime

import config
from models import RateRecord

log = logging.getLogger("cleaner")
_CODE = re.compile(r"^[A-Z]{3}$")
DATE_FORMATS = ("%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


@dataclass
class CleaningReport:
    source: str
    total: int = 0
    kept: int = 0
    invalid: int = 0
    missing_cash: int = 0
    duplicates: int = 0

    def to_dict(self):
        return asdict(self)


def parse_number(text, *, decimal=".", thousands=","):
    """Parse a positive number using explicitly specified separators."""
    if text is None:
        return None
    if (len(decimal) != 1 or (thousands and len(thousands) != 1)
            or decimal == thousands):
        raise ValueError("decimal and thousands must be distinct single characters")

    s = str(text).strip()
    decimal_pattern = re.escape(decimal)
    if thousands:
        thousands_pattern = re.escape(thousands)
        integer_pattern = (
            rf"(?:\d+|\d{{1,3}}(?:{thousands_pattern}\d{{3}})+)"
        )
    else:
        integer_pattern = r"\d+"
    if not re.fullmatch(rf"{integer_pattern}(?:{decimal_pattern}\d+)?", s):
        return None
    normalized = s.replace(thousands, "") if thousands else s
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    value = float(normalized)
    return value if math.isfinite(value) and value > 0 else None


def parse_date(text):
    """Thử nhiều định dạng ngày; trả 'YYYY-MM-DD' hoặc None."""
    s = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def clean_vcb(rows, fetched_at):
    rep, out = CleaningReport("vcb", total=len(rows)), []
    for r in rows:
        code = (r.get("code") or "").strip().upper()
        date = parse_date(r.get("datetime"))
        cash = parse_number(r.get("buy"), decimal=".", thousands=",")
        transfer = parse_number(r.get("transfer"), decimal=".", thousands=",")
        sell = parse_number(r.get("sell"), decimal=".", thousands=",")
        # Dữ liệu sai: thiếu mã/ngày/giá, hoặc giá bán < giá mua (vô lý).
        if (not _CODE.match(code) or date is None or transfer is None
                or sell is None or sell < transfer):
            rep.invalid += 1
            continue
        if cash is None:
            rep.missing_cash += 1
        out.append(RateRecord(
            source="vcb",
            date=date,
            fetched_at=fetched_at, base_ccy=code,
            currency_name=(r.get("name") or "").strip().title(),
            quote_ccy="VND", buy_cash=cash, buy_transfer=transfer, sell=sell,
            mid=round((transfer + sell) / 2, 4), spread=round(sell - transfer, 4),
            is_major=code in config.MAJOR))
    return out, rep


def clean_ecb(rows, fetched_at):
    """ECB trả 'số đơn vị ngoại tệ cho 1 USD' -> đổi sang 'USD cho 1 đơn vị' (mid = 1/rate)."""
    rep, out = CleaningReport("ecb", total=len(rows)), []
    for r in rows:
        code = (r.get("code") or "").strip().upper()
        rate = parse_number(r.get("rate"), decimal=".", thousands="")
        d = parse_date(r.get("date"))
        if not _CODE.match(code) or rate is None or d is None:
            rep.invalid += 1
            continue
        out.append(RateRecord(
            source="ecb", date=d, fetched_at=fetched_at, base_ccy=code,
            currency_name=config.NAMES.get(code, code), quote_ccy="USD",
            buy_cash=None, buy_transfer=None, sell=None,
            mid=round(1 / rate, 8), spread=None, is_major=code in config.MAJOR))
    return out, rep


def deduplicate(records):
    """Giữ bản ghi mới nhất cho mỗi khóa (source, date, base_ccy)."""
    seen = {}
    for r in records:
        seen[r.key] = r
    return list(seen.values()), len(records) - len(seen)


def clean_all(vcb_rows, ecb_rows, fetched_at):
    records, reports = [], []
    for fn, rows in ((clean_vcb, vcb_rows), (clean_ecb, ecb_rows)):
        if not rows:
            continue
        recs, rep = fn(rows, fetched_at)
        recs, rep.duplicates = deduplicate(recs)
        rep.kept = len(recs)
        records.extend(recs)
        reports.append(rep)
        log.info("Làm sạch %s: %s", rep.source, rep.to_dict())
    return records, reports
