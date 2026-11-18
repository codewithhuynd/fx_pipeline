"""Điều phối: Web/API -> Thu thập -> Làm sạch -> Cấu trúc -> File."""
"""Chương trình thực hiện các công việc theo thứ tự
1. Lấy dữ liệu từ các nguồn bên ngoài
2. Nhận dữ liệu từ các nguồn
3. Xử lý dữ liệu không hợp lệ
4. Chuẩn hóa dữ liệu về định dạng thống nhất
5. Lưu dữ liệu xuống file"""
import json
import logging
from datetime import datetime

import cleaner
import collector_ecb
import collector_vcb
import config
import storage

log = logging.getLogger("pipeline") 


def run(days=365, offline=False, vcb_only=False):
    """Thu thập và lưu dữ liệu; có thể chỉ chạy nguồn VCB cho tác vụ hằng ngày."""
    config.ensure_dirs()
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vcb_rows = collector_vcb.collect(offline=offline)
    ecb_rows = [] if offline or vcb_only else collector_ecb.collect(days)
    if not vcb_rows and not ecb_rows:
        log.error("Không thu thập được dữ liệu từ bất kỳ nguồn nào.")
        return None
    records, reports = cleaner.clean_all(vcb_rows, ecb_rows, fetched_at)
    if not records:
        log.error("Tất cả bản ghi đều không hợp lệ sau làm sạch.")
        return None
    allr = storage.merge_and_save(records)
    config.REPORT_PATH.write_text(
        json.dumps([r.to_dict() for r in reports], indent=2), encoding="utf-8")
    return allr, reports


"Mặc định hàm run lấy dữ liệu trong 365 ngày và trực tuyến"
    
