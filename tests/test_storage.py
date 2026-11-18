import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage  # noqa: E402


def test_load_csv_handles_empty_and_invalid_files(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    assert storage.load_csv(empty) == []

    wrong_header = tmp_path / "wrong-header.csv"
    wrong_header.write_text("not,a,rate,file\n1,2,3,4\n", encoding="utf-8")
    assert storage.load_csv(wrong_header) == []

    malformed = tmp_path / "malformed.csv"
    malformed.write_text('"unterminated', encoding="utf-8")
    assert storage.load_csv(malformed) == []

    invalid_encoding = tmp_path / "invalid-encoding.csv"
    invalid_encoding.write_bytes(b"\xff\xfe\xfa")
    assert storage.load_csv(invalid_encoding) == []


def test_load_csv_skips_rows_with_invalid_values_or_column_counts(tmp_path):
    path = tmp_path / "rates.csv"
    path.write_text(
        "source,date,fetched_at,base_ccy,currency_name,quote_ccy,buy_cash,"
        "buy_transfer,sell,mid,spread,is_major\n"
        "ecb,2026-01-01,2026-01-01 10:00:00,EUR,Euro,USD,,,,1.1,,True\n"
        "ecb,2026-01-01,2026-01-01 10:00:00,EUR,Euro,USD,,,,bad,,True\n"
        "ecb,2026-01-01\n",
        encoding="utf-8",
    )

    records = storage.load_csv(path)

    assert len(records) == 1
    assert records[0].base_ccy == "EUR"


def _rec(date, mid):
    from models import RateRecord
    return RateRecord("ecb", date, "2026-01-01 10:00:00", "EUR", "Euro",
                      "USD", None, None, None, mid, None, True)


def _use_tmp_paths(monkeypatch, tmp_path):
    import config
    for name in ("CSV_PATH", "JSON_PATH", "DB_PATH"):
        monkeypatch.setattr(config, name, tmp_path / getattr(config, name).name)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return config


def test_merge_keeps_history_when_csv_is_corrupted(monkeypatch, tmp_path):
    config = _use_tmp_paths(monkeypatch, tmp_path)
    storage.merge_and_save([_rec("2026-01-01", 1.1), _rec("2026-01-02", 1.2)])

    # Giả lập CSV bị hỏng (vd lưu lại bằng Excel làm đổi header)
    config.CSV_PATH.write_text("col1;col2\n1;2\n", encoding="utf-8")

    allr = storage.merge_and_save([_rec("2026-01-03", 1.3)])

    assert [r.date for r in allr] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert len(storage.load_csv(config.CSV_PATH)) == 3
    backups = list(tmp_path.glob("rates.broken_*.csv"))
    assert len(backups) == 1 and "col1;col2" in backups[0].read_text(encoding="utf-8")


def test_merge_first_run_creates_no_backup(monkeypatch, tmp_path):
    _use_tmp_paths(monkeypatch, tmp_path)
    allr = storage.merge_and_save([_rec("2026-01-01", 1.1)])
    assert len(allr) == 1
    assert not list(tmp_path.glob("*.broken_*"))
