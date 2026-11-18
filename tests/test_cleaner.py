import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import collector_vcb, collector_ecb, cleaner  # noqa: E402


def test_parse_number():
    assert cleaner.parse_number("25,100.00") == 25100.0
    assert cleaner.parse_number("51.77") == 51.77
    assert cleaner.parse_number("25.320,00", decimal=",", thousands=".") == 25320.0
    assert cleaner.parse_number("25,10.00") is None
    assert cleaner.parse_number("1,234.50", decimal=".", thousands="") is None
    for bad in ("-", "", None, "abc", "0", "-5"):
        assert cleaner.parse_number(bad) is None


def test_parse_date():
    assert cleaner.parse_date("1/15/2026 9:00:00 AM") == "2026-01-15"
    assert cleaner.parse_date("2026-01-15") == "2026-01-15"
    assert cleaner.parse_date("không phải ngày") is None


def test_vcb_parse_and_clean():
    xml = (Path(__file__).parent / "fixtures" / "vcb_sample.xml").read_text(encoding="utf-8")
    rows = collector_vcb.parse(xml)
    assert len(rows) == 8
    recs, rep = cleaner.clean_vcb(rows, "2026-01-15 10:00:00")
    assert rep.invalid == 2          # KRW (toàn dấu '-') và dòng hỏng XXX
    assert rep.missing_cash == 1     # THB thiếu giá mua tiền mặt
    usd = next(r for r in recs if r.base_ccy == "USD")
    assert usd.spread == 360.0 and usd.is_major and usd.date == "2026-01-15"


def test_vcb_rejects_invalid_date_instead_of_using_fetch_date():
    rows = [{"code": "USD", "buy": "25000", "transfer": "25030",
             "sell": "25390", "datetime": "not-a-date"}]

    records, report = cleaner.clean_vcb(rows, "2026-11-03 08:45:00")

    assert records == []
    assert report.invalid == 1
    assert report.kept == 0


def test_broken_inputs_do_not_crash():
    assert collector_vcb.parse("<ExrateList><oops>") == []
    assert collector_vcb.parse("<ExrateList></ExrateList>") == []
    assert collector_ecb.parse("{không phải json") == []
    assert collector_ecb.parse('{"foo": 1}') == []


def test_ecb_clean_and_dedupe():
    rows = [{"date": "2026-01-02", "code": "EUR", "rate": 0.8},
            {"date": "2026-01-02", "code": "EUR", "rate": 0.8},    # trùng
            {"date": "2026-01-02", "code": "JPY", "rate": "abc"},  # sai định dạng
            {"date": "hôm qua", "code": "GBP", "rate": 0.7}]       # sai ngày
    recs, rep = cleaner.clean_ecb(rows, "2026-01-03 00:00:00")
    recs, dup = cleaner.deduplicate(recs)
    assert rep.invalid == 2 and dup == 1 and len(recs) == 1
    assert abs(recs[0].mid - 1.25) < 1e-9
