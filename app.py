"""Giao diện Streamlit. Chạy: streamlit run app.py"""
import streamlit as st

import analyzer
import config
import storage
from pipeline import run

config.setup_logging()
st.set_page_config(page_title="Phân tích tỷ giá", layout="wide")
st.title("Thu thập và phân tích tỷ giá ngoại tệ")

with st.sidebar:
    st.header("Thu thập dữ liệu")
    days = st.slider("Số ngày lịch sử (ECB)", 7, 730, 365)
    offline = st.checkbox("Offline (dùng XML đã lưu)")
    if st.button("Thu thập mới"):
        with st.spinner("Đang thu thập..."):
            res = run(days, offline)
        if res is None:
            st.error("Không thu thập được dữ liệu. Xem logs/app.log.")
        else:
            st.success(f"Đã lưu {len(res[0])} bản ghi")
    fmt = st.selectbox("Đọc dữ liệu từ", ["csv", "json", "sqlite"])

df = analyzer.to_df(storage.load(fmt))
if df.empty:
    st.info("Chưa có dữ liệu. Bấm 'Thu thập mới'.")
    st.stop()

st.subheader("Tìm kiếm, lọc, sắp xếp")
c1, c2, c3, c4 = st.columns(4)
kw = c1.text_input("Từ khóa (mã/tên)")
src = c2.selectbox("Nguồn", ["Tất cả", "vcb", "ecb"])
codes = c3.multiselect("Ngoại tệ", sorted(df.base_ccy.unique()))
sort_by = c4.selectbox("Sắp xếp theo", ["date", "base_ccy", "mid", "spread"])
asc = c4.checkbox("Tăng dần")
major = st.checkbox("Chỉ ngoại tệ chính")

view = analyzer.search(df, kw) if kw else df
view = analyzer.filter_df(view, None if src == "Tất cả" else src, codes, major_only=major)
view = view.sort_values(sort_by, ascending=asc)
st.write(f"Kết quả: **{len(view)}** / {len(df)} bản ghi")
st.dataframe(view, use_container_width=True)

st.subheader("Thống kê")
for title, table, insight in analyzer.run_all(df):
    with st.expander(title, expanded=False):
        st.dataframe(table, use_container_width=True)
        st.info(insight)

st.subheader("Biểu đồ tỷ giá USD cho 1 đơn vị (ECB)")
p = df[df.source == "ecb"].pivot_table(index="date", columns="base_ccy", values="mid")
pick = st.multiselect("Chọn cặp", list(p.columns), default=[c for c in ["EUR", "GBP"] if c in p.columns])
if pick:
    st.line_chart(p[pick])
