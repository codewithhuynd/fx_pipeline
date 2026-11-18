"""Nguồn 2: Frankfurter API (JSON, dữ liệu ECB) - lịch sử tỷ giá theo ngày."""
import json
import logging
import time
from datetime import date, timedelta

import config
from collectors_http import http_get

log = logging.getLogger("ecb")


def parse(text):
    """JSON -> list[dict] thô. Trả về [] nếu sai định dạng."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        log.error("JSON sai định dạng: %s", e)
        return []
    rates = data.get("rates") if isinstance(data, dict) else None
    if not isinstance(rates, dict):
        log.error("JSON thiếu khóa 'rates'.")
        return []
    rows = []
    for d, per_day in rates.items():
        if not isinstance(per_day, dict):
            continue
        for code, val in per_day.items():
            rows.append({"source": "ecb", "date": d, "code": code,
                         "rate": val, "base": data.get("base", "USD")})
    return rows


def collect(days=365):
    end = date.today()
    cur = end - timedelta(days=days)
    rows = []
    while cur <= end:
        chunk_end = min(cur + timedelta(days=config.CHUNK_DAYS), end)
        text = http_get(f"{config.ECB_URL}/{cur}..{chunk_end}",
                        params={"base": "USD", "symbols": ",".join(config.ECB_SYMBOLS)})
        if text:
            rows.extend(parse(text))
        cur = chunk_end + timedelta(days=1)
        time.sleep(config.DELAY)
    log.info("ECB: %d dòng thô", len(rows))
    return rows
