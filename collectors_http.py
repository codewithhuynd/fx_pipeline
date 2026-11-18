"""Hàm tải HTTP dùng chung: retry, timeout, không bao giờ làm chương trình crash."""
import logging
import time

import requests

import config

log = logging.getLogger("http")


def http_get(url, params=None):
    """Trả về nội dung text (UTF-8) hoặc None nếu thất bại."""
    for attempt in range(1, config.RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers=config.HEADERS,
                             timeout=config.TIMEOUT)
            if r.status_code == 404:
                log.warning("404 Not Found: %s", url)
                return None
            r.raise_for_status()
            return r.content.decode("utf-8-sig", errors="replace")  # bỏ BOM nếu có
        except requests.RequestException as e:
            log.warning("Lỗi %s (lần %d/%d): %s", url, attempt, config.RETRIES, e)
            time.sleep(2 ** (attempt - 1))
    log.error("Bỏ cuộc sau %d lần: %s", config.RETRIES, url)
    return None
