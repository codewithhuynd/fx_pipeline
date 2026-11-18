"""Cấu hình tập trung: URL, đường dẫn, tham số. Không hardcode rải rác trong code."""
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
LOG_DIR = BASE_DIR / "logs"
FIXTURE_DIR = BASE_DIR / "tests" / "fixtures"

CSV_PATH = DATA_DIR / "rates.csv"
JSON_PATH = DATA_DIR / "rates.json"
DB_PATH = DATA_DIR / "rates.db"
REPORT_PATH = DATA_DIR / "cleaning_report.json"

# Nguồn 1: Vietcombank (XML, tỷ giá niêm yết VND)
VCB_URL = "https://portal.vietcombank.com.vn/UserControls/TVPortal.TyGia/pXML.aspx"
# Nguồn 2: Frankfurter (JSON, dữ liệu ECB, có lịch sử theo ngày, KHÔNG có VND)
ECB_URL = "https://api.frankfurter.dev/v1"
ECB_SYMBOLS = ["EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "SGD", "CNY", "KRW", "THB"]

MAJOR = {"USD", "EUR", "JPY", "GBP", "AUD"}
NAMES = {
    "USD": "US Dollar", "EUR": "Euro", "JPY": "Japanese Yen", "GBP": "British Pound",
    "AUD": "Australian Dollar", "CAD": "Canadian Dollar", "CHF": "Swiss Franc",
    "SGD": "Singapore Dollar", "CNY": "Chinese Yuan", "KRW": "South Korean Won",
    "THB": "Thai Baht",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (student-project; python-requests)"}
TIMEOUT = 15      # giây
RETRIES = 3       # số lần thử lại
DELAY = 1.0       # nghỉ giữa các request (lịch sự với server)
CHUNK_DAYS = 85   # chia nhỏ khoảng ngày để API không tự giảm độ phân giải


def ensure_dirs():
    for d in (DATA_DIR, RAW_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def setup_logging():
    ensure_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
                  logging.StreamHandler()],
    )
