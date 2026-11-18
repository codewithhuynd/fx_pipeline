"""Nguồn 1: Vietcombank (XML)."""
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import config
from collectors_http import http_get

log = logging.getLogger("vcb")

MIN_INTERVAL = 300  # VCB ghi rõ: chỉ 1 request mỗi 5 phút (300 giây)


def _save_raw(text):
    config.ensure_dirs()
    p = config.RAW_DIR / f"vcb_{datetime.now():%Y%m%d_%H%M%S}.xml"
    p.write_text(text, encoding="utf-8")


def _latest_raw():
    """Chế độ offline: đọc file XML đã lưu gần nhất (hoặc file mẫu trong tests/fixtures)."""
    files = sorted(config.RAW_DIR.glob("vcb_*.xml")) or \
        sorted(config.FIXTURE_DIR.glob("vcb_*.xml"))
    if not files:
        log.error("Chế độ offline nhưng không có file XML nào.")
        return None
    log.info("Offline: đọc %s", files[-1].name)
    return files[-1].read_text(encoding="utf-8-sig")


def _recent_raw():
    """Trả về XML đã tải cách đây dưới 5 phút (nếu có) để khỏi gọi lại VCB."""
    files = sorted(config.RAW_DIR.glob("vcb_*.xml"))
    if files and time.time() - files[-1].stat().st_mtime < MIN_INTERVAL:
        return files[-1].read_text(encoding="utf-8-sig")
    return None


def parse(xml_text):
    """XML -> list[dict] thô. Trả về [] nếu XML hỏng hoặc đổi cấu trúc."""
    try:
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError as e:
        log.error("XML sai định dạng: %s", e)
        return []
    stamp = root.findtext("DateTime")
    rows = [{
        "source": "vcb", "datetime": stamp,
        "code": e.get("CurrencyCode"), "name": e.get("CurrencyName"),
        "buy": e.get("Buy"), "transfer": e.get("Transfer"), "sell": e.get("Sell"),
    } for e in root.iter("Exrate")]
    if not rows:
        log.warning("Không có thẻ <Exrate>: có thể website đã đổi cấu trúc.")
    return rows


def collect(offline=False):
    fresh = False
    if offline:
        text = _latest_raw()
    else:
        text = _recent_raw()
        if text:
            log.info("Dùng lại XML vừa tải (<5 phút) để tuân thủ giới hạn của VCB")
        else:
            text = http_get(config.VCB_URL)
            fresh = True
    if not text:
        return []
    rows = parse(text)
    if fresh:
        if rows:
            _save_raw(text)  # chỉ lưu bản gốc hợp lệ để tái lập kết quả / demo offline
        else:
            log.warning("Không lưu XML thô vì phản hồi không chứa dữ liệu hợp lệ.")
    log.info("VCB: %d dòng thô", len(rows))
    return rows