"""Tìm kiếm, lọc, sắp xếp và 8 thống kê (mỗi thống kê: bảng + nhận xét)."""
import json
import unicodedata

import numpy as np
import pandas as pd

import config
from models import FIELD_NAMES


def to_df(records):
    if not records:
        df = pd.DataFrame(columns=FIELD_NAMES)
    else:
        df = pd.DataFrame([r.to_dict() for r in records])
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    df["fetched_at"] = pd.to_datetime(
        df["fetched_at"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    return df


def strip_accents(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


# ---------- Tìm kiếm / lọc / sắp xếp ----------
def search(df, keyword):
    """Tìm theo mã hoặc tên, không phân biệt hoa thường và dấu."""
    kw = strip_accents(keyword)
    mask = (df.base_ccy + " " + df.currency_name).apply(strip_accents).str.contains(kw, regex=False)
    return df[mask]


def filter_df(df, source=None, codes=None, date_from=None, date_to=None,
              major_only=False, min_mid=None, max_mid=None):
    out = df
    if source:
        out = out[out.source == source]
    if codes:
        out = out[out.base_ccy.isin([c.upper() for c in codes])]
    if date_from:
        dates = pd.to_datetime(out.date, format="%Y-%m-%d", errors="coerce")
        out = out[dates >= pd.Timestamp(date_from)]
    if date_to:
        dates = pd.to_datetime(out.date, format="%Y-%m-%d", errors="coerce")
        out = out[dates <= pd.Timestamp(date_to)]
    if major_only:
        out = out[out.is_major]
    if min_mid is not None:
        out = out[out.mid >= min_mid]
    if max_mid is not None:
        out = out[out.mid <= max_mid]
    return out


def sort_df(df, by=("date", "base_ccy"), ascending=(False, True)):
    """Sắp xếp đa tiêu chí."""
    return df.sort_values(list(by), ascending=list(ascending))


# ---------- Thống kê ----------
def _pivot(df):
    ecb = df[df.source == "ecb"]
    if ecb.empty:
        return pd.DataFrame()
    return ecb.pivot_table(index="date", columns="base_ccy", values="mid").sort_index()


def stat_describe(df):
    """[Mô tả] Phân phối tỷ giá và độ biến động từng ngoại tệ (ECB)."""
    p = _pivot(df)
    if p.empty:
        return None
    t = p.agg(["count", "mean", "median", "std", "min", "max"]).T
    t["cv_%"] = t["std"] / t["mean"] * 100
    top = t["cv_%"].idxmax()
    return ("1. Thống kê mô tả tỷ giá (USD cho 1 đơn vị, nguồn ECB)", t.round(5),
            f"{top} biến động mạnh nhất (hệ số biến thiên {t.loc[top, 'cv_%']:.2f}%); "
            f"CV cho phép so sánh độ biến động giữa các tiền có thang giá khác nhau.")


def stat_spread(df):
    """[Mô tả] Top 5 ngoại tệ có chênh lệch mua-bán lớn nhất tại VCB."""
    v = df[df.source == "vcb"]
    if v.empty:
        return None
    snap = v[v.date == v.date.max()].copy()
    snap["spread_%"] = snap.spread / snap.mid * 100
    t = snap.nlargest(5, "spread_%")[["base_ccy", "buy_transfer", "sell", "spread", "spread_%"]]
    return (f"2. Top 5 ngoại tệ có spread lớn nhất tại VCB (ngày {v.date.max()})",
            t.round(3).reset_index(drop=True),
            f"Spread cao nhất là {t.iloc[0].base_ccy} ({t.iloc[0]['spread_%']:.2f}%); "
            f"nhóm top 5 gồm {', '.join(t.base_ccy)}. "
            f"Nguyên nhân (thanh khoản, rủi ro tỷ giá...) cần kiểm chứng thêm, chỉ nên nêu như giả thuyết.")


def stat_cash_vs_transfer(df):
    """[So sánh] Mua tiền mặt rẻ hơn mua chuyển khoản bao nhiêu %."""
    v = df[(df.source == "vcb") & df.buy_cash.notna()]
    if v.empty:
        return None
    v = v[v.date == v.date.max()].copy()
    v["gap_%"] = (v.buy_transfer - v.buy_cash) / v.buy_transfer * 100
    med, avg = v["gap_%"].median(), v["gap_%"].mean()
    big = v[v["gap_%"] > med + 3].base_ccy.tolist()
    note = f" Ngoại lệ chênh lớn: {', '.join(big)}." if big else ""
    return ("3. Chênh lệch giá mua: tiền mặt so với chuyển khoản (VCB)",
            v[["base_ccy", "buy_cash", "buy_transfer", "gap_%"]].round(3).reset_index(drop=True),
            f"Đa số ngoại tệ VCB mua tiền mặt thấp hơn chuyển khoản khoảng {med:.2f}% (trung vị); "
            f"trung bình {avg:.2f}% bị kéo lên bởi ngoại lệ.{note}")


def stat_cross_rate(df):
    """[So sánh 2 nguồn] Tỷ giá chéo suy ra từ VCB so với thị trường (ECB)."""
    v = df[df.source == "vcb"]
    p = _pivot(df)
    if v.empty or p.empty:
        return None
    d = v.date.max()
    snap = v[v.date == d].set_index("base_ccy").mid
    p = p[p.index <= d]
    if "USD" not in snap.index or p.empty:
        return None
    ref, ecb = p.index[-1], p.iloc[-1]
    rows = [{"ccy": c, "VCB_suy_ra": snap[c] / snap["USD"], "ECB": ecb[c],
             "lệch_%": (snap[c] / snap["USD"] / ecb[c] - 1) * 100}
            for c in ecb.index if c in snap.index and pd.notna(ecb[c])]
    if not rows:
        return None
    t = pd.DataFrame(rows)
    gap = t["lệch_%"].abs().mean()
    verdict = ("tỷ giá VCB bám sát thị trường quốc tế" if gap < 1.5
               else "chênh lệch đáng kể, cần kiểm tra đơn vị yết giá, thời điểm lấy số liệu hoặc dữ liệu lỗi")
    return (f"4. Tỷ giá chéo X/USD: VCB (ngày {d}) so với ECB (ngày {ref})",
            t.round(5),
            f"Chênh lệch tuyệt đối trung bình {gap:.2f}%: {verdict}. Phần lệch bình thường đến từ "
            f"biên độ mua-bán và độ trễ thời gian giữa hai nguồn.")


def stat_extremes(df):
    """[Xu hướng] Ngày cao nhất / thấp nhất của từng cặp."""
    p = _pivot(df)
    if p.empty:
        return None
    t = pd.DataFrame({"ngày_cao_nhất": p.idxmax(), "giá_cao": p.max(),
                      "ngày_thấp_nhất": p.idxmin(), "giá_thấp": p.min()})
    t["giá_cao"] = t["giá_cao"].round(5)
    t["giá_thấp"] = t["giá_thấp"].round(5)
    return ("5. Ngày đạt tỷ giá cao nhất / thấp nhất trong kỳ", t,
            f"Biên độ (cao/thấp) lớn nhất ở {(p.max() / p.min()).idxmax()} "
            f"({(p.max() / p.min()).max() * 100 - 100:.1f}%).")


def stat_change(df):
    """[Xu hướng] % thay đổi từ đầu kỳ đến cuối kỳ."""
    p = _pivot(df)
    if p.empty:
        return None
    ch = p.apply(lambda s: (s.dropna().iloc[-1] / s.dropna().iloc[0] - 1) * 100
                 if s.notna().sum() >= 2 else float("nan")).dropna().sort_values(ascending=False)
    if ch.empty:
        return None
    t = ch.round(2).rename("thay_đổi_%").to_frame()
    return (f"6. % thay đổi so với đầu kỳ ({p.index[0]} -> {p.index[-1]})", t,
            f"{ch.index[0]} mạnh lên nhiều nhất so với USD ({ch.iloc[0]:+.2f}%), "
            f"{ch.index[-1]} đứng cuối bảng ({ch.iloc[-1]:+.2f}%).")


def stat_correlation(df):
    """[Phân bố/tương quan] Tương quan biến động ngày giữa các ngoại tệ."""
    p = _pivot(df)
    if p.empty or len(p) < 3:
        return None
    c = p.pct_change().corr()
    pairs = c.where(np.triu(np.ones(c.shape, dtype=bool), k=1)).stack()
    if pairs.empty:
        return None
    a, b = pairs.abs().idxmax()
    v = pairs.loc[(a, b)]
    direction = "cùng chiều" if v > 0 else "ngược chiều" if v < 0 else "không tương quan"
    return ("7. Ma trận tương quan biến động theo ngày", c.round(2),
            f"Cặp {a}-{b} có tương quan mạnh nhất theo trị tuyệt đối "
            f"({v:.2f}; biến động {direction}).")


def stat_quality(df=None):
    """[Chất lượng dữ liệu] Tỷ lệ bản ghi lỗi/thiếu/trùng lúc làm sạch."""
    try:
        data = json.loads(config.REPORT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    t = pd.DataFrame(data)
    if t.empty:
        return None
    t["invalid_%"] = (t.invalid / t.total * 100).round(2)
    return ("8. Chất lượng dữ liệu sau làm sạch (lần chạy gần nhất)", t,
            f"Tỷ lệ bản ghi bị loại: " + ", ".join(f"{r.source}={r['invalid_%']}%" for _, r in t.iterrows()) + ".")


ALL_STATS = [stat_describe, stat_spread, stat_cash_vs_transfer, stat_cross_rate,
             stat_extremes, stat_change, stat_correlation, stat_quality]


def run_all(df):
    """Chạy toàn bộ thống kê; thống kê thiếu dữ liệu sẽ bị bỏ qua, không làm crash."""
    return [r for r in (fn(df) for fn in ALL_STATS) if r]


def print_all(df):
    results = run_all(df)
    if not results:
        print("Không đủ dữ liệu để thống kê.")
    for title, table, insight in results:
        print(f"\n=== {title} ===")
        print(table.to_string())
        print(f"-> Nhận xét: {insight}")
