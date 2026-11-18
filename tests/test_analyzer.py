import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

import analyzer  # noqa: E402
from models import RateRecord  # noqa: E402


def test_to_df_uses_datetime_columns_and_filters_date_bounds():
    records = [
        RateRecord("ecb", "2026-01-01", "2026-01-02 12:30:00", "EUR", "Euro",
                   "USD", None, None, None, 1.1, None, True),
        RateRecord("ecb", "2026-01-03", "2026-01-04 12:30:00", "EUR", "Euro",
                   "USD", None, None, None, 1.2, None, True),
    ]

    df = analyzer.to_df(records)

    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_datetime64_any_dtype(df["fetched_at"])
    filtered = analyzer.filter_df(df, date_from="2026-01-02", date_to="2026-01-03")
    assert filtered["date"].tolist() == [pd.Timestamp("2026-01-03")]


def test_stat_correlation_selects_strongest_negative_pair():
    returns = {
        "A": [0.01, 0.02, 0.03, 0.04, 0.05],
        "B": [-0.01, -0.02, -0.03, -0.04, -0.05],
        "C": [0.05, -0.02, 0.04, -0.01, 0.03],
    }
    rates = {code: [1.0] for code in returns}
    for code, changes in returns.items():
        for change in changes:
            rates[code].append(rates[code][-1] * (1 + change))

    df = pd.DataFrame([
        {"source": "ecb", "date": f"2026-01-{day:02d}",
         "base_ccy": code, "mid": rate}
        for code, values in rates.items()
        for day, rate in enumerate(values, start=1)
    ])

    result = analyzer.stat_correlation(df)

    assert result is not None
    assert "A-B" in result[2]
    assert "-1.00" in result[2]
    assert "ngược chiều" in result[2]
