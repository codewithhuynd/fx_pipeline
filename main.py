"""Menu dòng lệnh. Chạy: python main.py"""
import argparse

import config
import analyzer
import storage
from cleaner import parse_date
from pipeline import run

COLS = ["source", "date", "base_ccy", "quote_ccy", "buy_transfer", "sell", "mid", "spread"]


def show(df, n=15):
    if df.empty:
        print("Không có kết quả.")
        return
    print(df[COLS].head(n).to_string(index=False))
    print(f"... tổng {len(df)} dòng")


def read_int(prompt, default, lo, hi):
    s = input(f"{prompt} [{default}]: ").strip()
    if not s:
        return default
    try:
        v = int(s)
    except ValueError:
        print("Vui lòng nhập số nguyên.")
        return None
    if not lo <= v <= hi:
        print(f"Giá trị phải trong khoảng {lo}-{hi}.")
        return None
    return v


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collect and analyze foreign exchange rates.")
    parser.add_argument(
        "--vcb-only",
        action="store_true",
        help="Collect Vietcombank rates only; do not show the menu or call ECB.",
    )
    args = parser.parse_args(argv)

    config.setup_logging()
    if args.vcb_only:
        result = run(vcb_only=True)
        if result is None:
            print("VCB collection failed. See logs/app.log.")
            return 1
        records, reports = result
        vcb_records = sum(report.kept for report in reports if report.source == "vcb")
        print(f"Saved {vcb_records} VCB records; {len(records)} records in total.")
        return 0

    df = analyzer.to_df([])
    while True:
        print("\n1.Thu thập  2.Đọc file  3.Tìm kiếm  4.Lọc  5.Sắp xếp  6.Thống kê  7.SQL  0.Thoát")
        c = input("Chọn: ").strip()
        if c == "1":
            days = read_int("Số ngày lịch sử ECB", 365, 7, 1500)
            if days is None:
                continue
            offline = input("Chế độ offline (dùng XML đã lưu)? y/N: ").lower() == "y"
            res = run(days, offline)
            if res is None:
                print("Không thu thập được dữ liệu. Xem logs/app.log.")
                continue
            records, reports = res
            df = analyzer.to_df(records)
            print(f"Đã lưu {len(records)} bản ghi vào data/ (CSV + JSON + SQLite)")
            for r in reports:
                print("  ", r.to_dict())
        elif c == "2":
            fmt = input("Định dạng (csv/json/sqlite) [csv]: ").strip().lower() or "csv"
            if fmt not in ("csv", "json", "sqlite"):
                print("Định dạng không hợp lệ.")
                continue
            df = analyzer.to_df(storage.load(fmt))
            print(f"Đã đọc {len(df)} bản ghi từ {fmt}")
        elif c in ("3", "4", "5", "6") and df.empty:
            print("Chưa có dữ liệu. Chọn 1 (thu thập) hoặc 2 (đọc file) trước.")
        elif c == "3":
            show(analyzer.search(df, input("Từ khóa (mã hoặc tên): ")))
        elif c == "4":
            src = input("Nguồn (vcb/ecb, Enter=tất cả): ").strip().lower() or None
            codes = [x for x in input("Mã ngoại tệ (vd USD,EUR): ").replace(" ", "").split(",") if x]
            d1 = input("Từ ngày (YYYY-MM-DD): ").strip() or None
            d2 = input("Đến ngày (YYYY-MM-DD): ").strip() or None
            if (d1 and not parse_date(d1)) or (d2 and not parse_date(d2)):
                print("Ngày không hợp lệ.")
                continue
            major = input("Chỉ ngoại tệ chính? y/N: ").lower() == "y"
            show(analyzer.filter_df(df, src, codes, d1, d2, major))
        elif c == "5":
            by = [x for x in input("Sắp xếp theo cột (vd date,mid): ").replace(" ", "").split(",") if x]
            if not by or any(b not in df.columns for b in by):
                print("Cột không hợp lệ. Các cột:", ", ".join(df.columns))
                continue
            asc = input("Tăng dần? y/N: ").lower() == "y"
            show(analyzer.sort_df(df, by, [asc] * len(by)))
        elif c == "6":
            analyzer.print_all(df)
        elif c == "7":
            for row in storage.sql_summary():
                print(row)
        elif c == "0":
            break
        else:
            print("Lựa chọn không hợp lệ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
