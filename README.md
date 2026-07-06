# Hệ thống Quản lý Thư viện - Demo Django

## 1. Cài đặt

```bash
pip install -r requirements.txt
```

```python
import pymysql
pymysql.install_as_MySQLdb()
```

## 2. Tạo CSDL

```bash
mysql -u root -p < quanlythuvien-2_7_26.sql ----- Có chạy file sql rồi thì không cần chạy lệnh này
```

## 3. Cấu hình kết nối

Mặc định `thuvien_django/settings.py`: HOST=127.0.0.1, PORT=3306,
NAME=QuanLyThuVien, USER=root, PASSWORD="" (Tự đánh pass hoặc set biến môi trường note ở dưới).

```bash
export DB_USER=root
export DB_PASSWORD=your_password
```

## 4. Chạy thử

Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force (Xóa pycache)

```bash
python manage.py runserver
```

Mở trình duyệt: http://127.0.0.1:8000/

## 5. Sơ đồ trang (menu chính - đặt tên theo nghiệp vụ thư viện)

| Menu hiển thị | URL | Thực chất demo thuộc tính |
|---|---|---|
| Danh mục & tra cứu | `/danh-muc/` | VIEW |
| Tính ngày trễ hạn | `/tra-cuu-tre-han/` | FUNCTION |
| Mượn / Trả sách | `/muon-tra-sach/` | TRIGGER |
| Nghiệp vụ khác | `/nghiep-vu/` | STORED PROCEDURE |
| Điều chỉnh kho | `/dieu-chinh-kho/` | Demo Lost Update |
| Kiểm tra nhanh SL | `/kiem-tra-nhanh/` | Demo Dirty Read |
| Xác nhận tồn kho | `/xac-nhan-ton-kho/` | Demo Non-repeatable Read |
| Thống kê thể loại | `/thong-ke-the-loai/` | Demo Phantom Read |
| (link nhỏ ở footer) | `/he-thong/` | Trang kỹ thuật liệt kê toàn bộ đối tượng CSDL |

## 6. Lưu ý * ĐỌC KỸ CÁI LƯU Ý

- Các thủ tục tạo lỗi/fix có `DO SLEEP(10)` hoặc `SLEEP(15)` — mỗi lượt bấm
  nút sẽ "treo" khoảng 10-20 giây, đây là chủ đích để đủ thời gian
  chuyển sang tab kia thao tác, không phải lỗi hệ thống.
- Trang "Thống kê thể loại" (Phantom Read) có nút "Reset dữ liệu demo"
  — bấm 1 lần trước mỗi lượt chạy để số liệu ổn định.