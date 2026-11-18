"""Cấu trúc dữ liệu chung cho mọi nguồn (12 thuộc tính)."""
from dataclasses import dataclass, asdict, fields
from typing import Optional


@dataclass
class RateRecord:
    source: str                    # "vcb" | "ecb"
    date: str                      # YYYY-MM-DD
    fetched_at: str                # thời điểm thu thập
    base_ccy: str                  # ngoại tệ được định giá, vd USD
    currency_name: str
    quote_ccy: str                 # "VND" (vcb) hoặc "USD" (ecb)
    buy_cash: Optional[float]      # mua tiền mặt (chỉ vcb)
    buy_transfer: Optional[float]  # mua chuyển khoản (chỉ vcb)
    sell: Optional[float]          # bán (chỉ vcb)
    mid: float                     # giá giữa: vcb=(mua CK+bán)/2 ; ecb=USD cho 1 đơn vị
    spread: Optional[float]        # bán - mua chuyển khoản (chỉ vcb)
    is_major: bool                 # thuộc nhóm ngoại tệ chính

    def to_dict(self):
        return asdict(self)

    @property
    def key(self):
        return (self.source, self.date, self.base_ccy)


FIELD_NAMES = [f.name for f in fields(RateRecord)]
