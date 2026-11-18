# Thu thập và phân tích tỷ giá ngoại tệ (Bài A2)

Pipeline: **Web/API → Thu thập → Làm sạch → Cấu trúc dữ liệu → File (CSV/JSON/SQLite) → Tìm kiếm/Lọc/Sắp xếp → Thống kê**

## Nguồn dữ liệu
| Nguồn | Loại | Nội dung |
|---|---|---|
| Vietcombank (`pXML.aspx`) | XML | Tỷ giá niêm yết VND: mua tiền mặt, mua chuyển khoản, bán |
| Frankfurter API (dữ liệu ECB) | JSON | Lịch sử tỷ giá ngoại tệ/USD theo ngày (không có VND) |

## Cài đặt và chạy
```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python main.py                   # menu dòng lệnh
streamlit run app.py             # giao diện web (tùy chọn)
python -m pytest tests           # chạy unit test
```
Chạy menu `1` mỗi ngày để dữ liệu VCB tích lũy theo thời gian (tự gộp, bỏ trùng).
Chế độ **offline** dùng file XML đã lưu trong `data/raw/` (nếu chưa có thì dùng dữ liệu **mẫu giả lập** trong `tests/fixtures/`, không phải tỷ giá thật).

### Tự động thu thập VCB hằng ngày trên Windows

Lệnh dưới đây chỉ thu thập Vietcombank, không mở menu và không gọi ECB:

```powershell
.\venv\Scripts\python.exe main.py --vcb-only
```

Tác vụ Windows **FX Pipeline - Daily VCB** được lên lịch chạy lúc **09:00 mỗi ngày** bằng Python trong `venv`. Máy cần bật và người dùng cần đăng nhập; nếu máy tạm tắt hoặc tác vụ bị trễ, Task Scheduler được cấu hình chạy bù khi có thể. Kiểm tra trạng thái trong **Task Scheduler > Task Scheduler Library** hoặc xem `logs/app.log`. Có thể chạy lệnh trên thủ công để kiểm tra mà không chờ đến lịch.

## Cấu trúc
```
config.py            URL, đường dẫn, tham số, logging
models.py            dataclass RateRecord (12 thuộc tính)
collectors_http.py   http_get: retry + timeout + backoff
collector_vcb.py     nguồn XML       collector_ecb.py   nguồn JSON
cleaner.py           làm sạch, kiểm tra hợp lệ, báo cáo làm sạch
storage.py           CSV / JSON / SQLite, gộp dữ liệu nhiều lần chạy
analyzer.py          tìm kiếm, lọc, sắp xếp, 8 thống kê
pipeline.py          điều phối toàn bộ pipeline
main.py / app.py     CLI / Streamlit
tests/               unit test + dữ liệu mẫu
```
Khi chuyển bản ghi sang DataFrame, `date` và `fetched_at` được parse thành kiểu ngày/giờ; file CSV/JSON vẫn lưu ngày dạng ISO để dễ đọc và trao đổi.

## Đối chiếu yêu cầu
| Yêu cầu | Vị trí |
|---|---|
| 1. ≥1 nguồn | `collector_vcb.py`, `collector_ecb.py` (2 nguồn, 2 định dạng) |
| 3. ≥5 thuộc tính | 12 thuộc tính trong `models.py` |
| 4. Làm sạch | `cleaner.py` (regex, kiểm tra logic giá, bỏ trùng, báo cáo) |
| 5. Cấu trúc Python | `RateRecord` (dataclass), `list[RateRecord]`, DataFrame |
| 6–7. Lưu/đọc | `storage.py` (CSV, JSON, SQLite) |
| 8. Tìm kiếm/lọc | `analyzer.search`, `analyzer.filter_df` |
| 9. Sắp xếp | `analyzer.sort_df` (đa tiêu chí) |
| 10. ≥3 thống kê | 8 thống kê kèm nhận xét (`analyzer.py`) |
| 11. Xử lý lỗi | retry/404, XML/JSON hỏng, dòng sai định dạng, mất một nguồn vẫn chạy, file thiếu/hỏng |

## Hạn chế
- Phụ thuộc cấu trúc XML của Vietcombank và sự sẵn sàng của hai API; nếu đổi sẽ có cảnh báo trong `logs/app.log`.
- Dữ liệu VCB chỉ có lịch sử từ ngày bắt đầu chạy chương trình.
- ECB là tỷ giá tham chiếu theo ngày làm việc, không phải giá giao dịch.

## Thành viên
(điền tên, MSSV, phân công)
