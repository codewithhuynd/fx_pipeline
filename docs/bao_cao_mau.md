# Khung báo cáo A2 (điền số liệu và ảnh chụp thật của nhóm)

## I. Giới thiệu (1 trang)
- Bài toán: theo dõi tỷ giá VND của Vietcombank và đối chiếu với thị trường quốc tế (ECB).
- Vì sao hữu ích: người đổi ngoại tệ muốn biết ngân hàng chênh bao nhiêu, ngoại tệ nào biến động mạnh.
- Mục tiêu: pipeline Web/API → thống kê, 2 nguồn, 12 thuộc tính, ≥ 8 thống kê.

## II. Cơ sở lý thuyết (2–3 trang)
HTTP request/response, mã trạng thái; XML (ElementTree) và JSON; regex; dataclass/OOP; CSV/JSON/SQLite;
pandas (pivot_table, groupby, pct_change, corr); khái niệm tỷ giá mua/bán, spread, tỷ giá chéo, hệ số biến thiên.

## III. Phân tích và thiết kế
1. Sơ đồ pipeline (vẽ draw.io):  `VCB XML / Frankfurter JSON → collector → cleaner → RateRecord → CSV/JSON/SQLite → analyzer → CLI/Streamlit`
2. Bảng thuộc tính (12 dòng): tên | kiểu | nguồn | cách làm sạch. Lấy từ `models.py`.
3. Quy tắc làm sạch: bỏ dấu phẩy ngàn; `-` thành thiếu; giá bán < giá mua bị loại; ECB đổi `1/rate` để thành "USD cho 1 đơn vị"; bỏ trùng theo (source, date, base_ccy).
4. Sơ đồ module và luồng dữ liệu.
5. Vì sao 2 nguồn: VCB cho VND nhưng chỉ có "ảnh chụp"; ECB không có VND nhưng có lịch sử theo ngày. Hai nguồn gặp nhau ở thống kê tỷ giá chéo.

## IV. Cài đặt và kiểm thử
- Giải thích từng module (ngắn).
- **Báo cáo làm sạch thật** (chụp từ `data/cleaning_report.json`): tổng / giữ / loại / thiếu / trùng cho từng nguồn.
- **Bảng thử lỗi** (mỗi dòng 1 ảnh chụp log):

| Tình huống | Cách tạo | Kết quả mong đợi |
|---|---|---|
| Mất mạng | Tắt Wi-Fi rồi thu thập | Retry 3 lần, báo lỗi, không crash |
| API sai | Đổi `ECB_URL` thành URL sai | Nguồn ECB bỏ qua, VCB vẫn chạy |
| XML hỏng | Sửa file trong `data/raw/` rồi chạy offline | "XML sai định dạng", trả về rỗng |
| XML đổi cấu trúc | Đổi `Exrate` thành tên khác | Cảnh báo "website đã đổi cấu trúc" |
| JSON hỏng | Xóa dấu `}` trong `rates.json` | "File JSON bị hỏng", không crash |
| Dòng CSV lỗi | Sửa `mid` thành `abc` | Bỏ qua dòng đó, đọc tiếp |
| Chưa có file | Xóa `data/` rồi chọn "Đọc file" | Thông báo thu thập trước |
| Nhập sai | Nhập chữ ở ô số ngày | Báo lỗi, quay lại menu |

- Kết quả unit test (chụp `pytest`).
- Mỗi thống kê: **Câu hỏi → Bảng/biểu đồ → Nhận xét**. Dùng 8 thống kê của `analyzer.py`, và tự viết lại nhận xét bằng số liệu thật của nhóm.

## V. Đánh giá và cải tiến
- Hạn chế: xem README. Thêm: lịch sử VCB ngắn, chưa có giá vàng.
- Mở rộng: thêm nguồn giá vàng, lịch chạy tự động hằng ngày (Task Scheduler/cron), cảnh báo khi spread vượt ngưỡng, dự đoán xu hướng (phần mở rộng).

## VI. Kết luận
Kết quả đạt được (con số cụ thể), bài học (kiểm tra website trước khi code, tách module, ghi log).

## VII. Tài liệu tham khảo (APA 7, kiểm tra lại năm và URL trước khi nộp)
- Frankfurter. (n.d.). *Frankfurter API documentation*. https://frankfurter.dev
- Joint Stock Commercial Bank for Foreign Trade of Vietnam. (n.d.). *Tỷ giá ngoại tệ* [Website]. https://www.vietcombank.com.vn
- Python Software Foundation. (n.d.). *xml.etree.ElementTree: The ElementTree XML API*. https://docs.python.org/3/library/xml.etree.elementtree.html
- Python Software Foundation. (n.d.). *dataclasses: Data classes*. https://docs.python.org/3/library/dataclasses.html
- The pandas development team. (n.d.). *pandas documentation*. https://pandas.pydata.org/docs/
