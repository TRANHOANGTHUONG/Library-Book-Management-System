PHẦN A. ÁNH XẠ MENU GIAO DIỆN <-> THUỘC TÍNH CSDL
------------------------------------------------------------------

Menu "Danh mục & tra cứu"  (URL /danh-muc/)
  -> Thuộc tính: VIEW
  -> Đối tượng dùng: vw_DanhMucSach, vw_LichSuMuonSach, vw_SachDangMuon,
     vw_TopSachYeuThich, vw_DocGiaTreHan
  -> Giải thích khi trình bày: "Mỗi lựa chọn trong dropdown ở trang này
     chạy trực tiếp SELECT * FROM <tên view>, tức đang dùng đối tượng VIEW."

Menu "Tính ngày trễ hạn"  (URL /tra-cuu-tre-han/)
  -> Thuộc tính: FUNCTION
  -> Đối tượng dùng: fn_SoNgayTreHan(HanTra, NgayTra)
  -> Giải thích: "Form này gọi trực tiếp SELECT fn_SoNgayTreHan(...), một
     FUNCTION do người dùng định nghĩa (User-Defined Function)."

Menu "Mượn / Trả sách"  (URL /muon-tra-sach/)
  -> Thuộc tính: TRIGGER
  -> Đối tượng dùng: trg_KiemTraTonKho (BEFORE INSERT), trg_GiamSoLuongSach
     (AFTER INSERT), trg_TangSoLuongKhiTra (AFTER UPDATE) — cả 3 đều gắn
     trên bảng ChiTietPhieuMuon.
  -> Giải thích: "Khi bấm 'Lập phiếu mượn', hệ thống gọi procedure
     sp_LapPhieuMuon để INSERT vào ChiTietPhieuMuon; ngay lúc đó 2 trigger
     BEFORE/AFTER INSERT tự động chạy để kiểm tra tồn kho và trừ SoLuong —
     không có dòng code nào trong Django tự trừ số lượng cả, hoàn toàn do
     trigger xử lý. Tương tự khi 'Trả sách' (UPDATE) sẽ kích hoạt
     trg_TangSoLuongKhiTra."

Menu "Nghiệp vụ khác"  (URL /nghiep-vu/)
  -> Thuộc tính: STORED PROCEDURE (2 procedure còn lại chưa dùng ở trang
     Mượn/Trả)
  -> Đối tượng dùng: sp_ThemSachMoi, sp_ThanhToanPhat
     (sp_LapPhieuMuon và sp_TraSach_VaXuLyPhat đã demo ở trang Mượn/Trả)
  -> Giải thích: "Toàn bộ nghiệp vụ ghi dữ liệu trong hệ thống này (mượn,
     trả, thêm sách, thanh toán phạt) đều KHÔNG dùng Django ORM để tự
     INSERT/UPDATE trực tiếp, mà gọi CALL đến 4 stored procedure có sẵn
     trong CSDL — đảm bảo logic nghiệp vụ (kiểm tra tồn kho, tính tiền
     phạt...) nằm ở tầng CSDL, đúng yêu cầu đồ án."

Trang "Xem tổng quan kỹ thuật hệ thống" (URL /he-thong/, chỉ có link nhỏ
ở footer, KHÔNG nằm trong menu chính)
  -> Trang phụ để tự đối chiếu số lượng bảng/view/function/trigger/
     procedure thực tế đang có trong CSDL (đọc từ information_schema),
     dùng khi giảng viên hỏi "có đúng đủ 4 thuộc tính không".


PHẦN B. ÁNH XẠ 4 TRANG "THAO TÁC ĐỒNG THỜI" <-> 4 BUG
------------------------------------------------------------------

"Điều chỉnh kho"      (/dieu-chinh-kho/)     -> LOST UPDATE
"Kiểm tra nhanh SL"   (/kiem-tra-nhanh/)     -> DIRTY READ
"Xác nhận tồn kho"    (/xac-nhan-ton-kho/)   -> NON-REPEATABLE READ
"Thống kê thể loại"   (/thong-ke-the-loai/)  -> PHANTOM READ

Mỗi trang có nút chuyển "Phiên bản xử lý": TRƯỚC (gây lỗi) / SAU (đã fix).
Mỗi trang có 2 form riêng biệt: "Thao tác của Thủ thư A" và "Thao tác của
Thủ thư B" — đây chính là 2 request HTTP độc lập, mỗi request tự mở 1 kết
nối MySQL riêng khi Django xử lý. KHÔNG có bất kỳ đoạn JavaScript nào tự
động bấm giùm — người dùng phải tự mở 2 tab trình duyệt và tự bấm tay
theo đúng thời điểm mô tả bên dưới.


PHẦN C. KỊCH BẢN THAO TÁC TAY CHI TIẾT (2 TAB TRÌNH DUYỆT)
------------------------------------------------------------------

Chuẩn bị chung: mở trình duyệt, tạo sẵn 2 tab cùng trỏ tới trang tương
ứng, ví dụ cả 2 tab cùng mở http://127.0.0.1:8000/dieu-chinh-kho/


### C.1 LOST UPDATE — Trang "Điều chỉnh kho"

Tình huống nghiệp vụ: Cuốn "Ly thuyet Tinh toan" (MaSach = 1) hiện có 10
cuốn. Thủ thư A vừa nhập thêm 5 cuốn mới mua (+5). Cùng lúc đó Thủ thư B
phát hiện 2 cuốn bị mốc phải loại khỏi kho (-2). Nếu xử lý đúng, kết quả
cuối phải là 10 + 5 - 2 = 13.

Bước demo LỖI (chọn "Trước khi xử lý đồng thời"):
  1. Tab 1: chọn sách MaSach=1, ô "Số lượng cộng/trừ" = 5, bấm "Áp dụng"
     (đây là Thủ thư A). Trình duyệt sẽ bắt đầu "quay" (loading) khoảng
     10 giây — đây là lúc procedure vừa đọc xong SoLuong=10 và đang
     SLEEP(10) trước khi ghi lại.
  2. NGAY khi thấy Tab 1 đang loading (trong vòng 1-2 giây đầu), chuyển
     qua Tab 2: chọn cùng sách MaSach=1, ô "Số lượng cộng/trừ" = -2, bấm
     "Áp dụng" (Thủ thư B).
  3. Đợi cả 2 tab load xong (mỗi tab hiện kết quả procedure của mình).
  4. Vào trang "Mượn / Trả sách" (hoặc F5 lại "Điều chỉnh kho") để xem
     SoLuong cuối cùng của MaSach=1.
  5. Kết quả LỖI: SoLuong cuối KHÔNG bằng 13 (thường sẽ là 15 hoặc 8,
     tuỳ ai ghi đè sau) — vì cả 2 session cùng đọc giá trị gốc là 10
     trước khi thao tác kia kịp ghi, nên một trong hai lần cộng/trừ đã
     bị mất (Lost Update).

Bước demo ĐÃ FIX (chọn "Sau khi xử lý đồng thời"), lặp lại đúng thao
tác 1-4 ở trên:
  - Lần này Tab 2 (Thủ thư B) sẽ KHÔNG chạy ngay khi bấm, mà phải "chờ"
    (loading lâu hơn bình thường) cho tới khi Tab 1 (Thủ thư A) xử lý
    xong — vì stored procedure fix dùng SELECT ... FOR UPDATE (khoá bi
    quan) nên Session B phải đợi Session A nhả khoá.
  - Kết quả: SoLuong cuối = 13 (đúng cả 2 lần cộng/trừ).
  - Điểm nhấn khi trình bày: chính việc Tab 2 bị "chờ" lâu hơn là bằng
    chứng trực quan nhất cho thấy khoá bi quan đang hoạt động.


### C.2 DIRTY READ — Trang "Kiểm tra nhanh SL"

Tình huống nghiệp vụ: Sách "Nhung nguoi khon kho" (MaSach = 2, đang có 5
cuốn) bị nghi nhập sai. Thủ thư A thử sửa tạm thành 999 để kiểm tra rồi
sẽ huỷ ngay (rollback) sau 15 giây. Thủ thư B đang tra cứu số lượng cuốn
này cho độc giả đúng lúc đó.

Bước demo LỖI (chọn "Trước khi xử lý đồng thời"):
  1. Tab 1: chọn MaSach=2, ô "Số lượng nhập tạm (nhầm)" = 999, bấm
     "Sửa tạm & tự huỷ sau 15 giây" (Thủ thư A). Tab này sẽ loading
     khoảng 15 giây.
  2. Trong khoảng giây thứ 2-5 sau khi bấm Tab 1 (lúc Sach.SoLuong trong
     DB thực tế đã bị UPDATE tạm thành 999 nhưng CHƯA COMMIT), chuyển
     qua Tab 2: chọn MaSach=2, bấm "Xem số lượng hiện tại" (Thủ thư B).
  3. Kết quả LỖI: Tab 2 hiện SoLuong_DocDuoc_Rac = 999 — Thủ thư B vừa
     đọc trúng dữ liệu "rác" sắp bị huỷ (vì dùng READ UNCOMMITTED).
  4. Đợi Tab 1 chạy xong (tự ROLLBACK), F5 lại trang để thấy SoLuong
     thật trong DB vẫn là 5 — chứng minh giá trị 999 mà Thủ thư B đọc
     được lúc nãy chưa từng tồn tại thật sự.

Bước demo ĐÃ FIX (chọn "Sau khi xử lý đồng thời"), lặp lại thao tác 1-2:
  - Tab 2 lúc này gọi thủ tục dùng READ COMMITTED, nên chỉ đọc được giá
    trị đã COMMIT thật sự — kết quả SoLuong_DocDuoc_AnToan = 5 (không
    bao giờ thấy số 999), dù bấm đúng thời điểm giữa lúc Tab 1 đang xử
    lý.


### C.3 NON-REPEATABLE READ — Trang "Xác nhận tồn kho"

Tình huống nghiệp vụ: Trước khi duyệt một phiếu mượn quan trọng, quy
trình yêu cầu Thủ thư A xác nhận số lượng tồn kho MaSach=1 hai lần (cách
nhau vài giây) để chắc chắn số liệu ổn định. Thủ thư B tranh thủ cập
nhật lại kho ngay giữa lúc đó.

Bước demo LỖI (chọn "Trước khi xử lý đồng thời"):
  1. Tab 1: chọn MaSach=1, bấm "Bắt đầu xác nhận" (Thủ thư A). Tab này
     sẽ đọc lần 1 rồi loading khoảng 10 giây trước khi đọc lần 2.
  2. Trong 10 giây đó, chuyển qua Tab 2: chọn MaSach=1, ô "Cập nhật số
     lượng thành" = 123, bấm "Lưu ngay" (Thủ thư B). Thao tác này COMMIT
     gần như ngay lập tức.
  3. Đợi Tab 1 load xong, xem kết quả: SoLuong_Lan1 khác SoLuong_Lan2
     (lần 2 đã thấy giá trị 123 mà Tab 2 vừa ghi) — mặc dù cả 2 lần đọc
     đều nằm trong CÙNG một transaction của Thủ thư A. Đây là
     Non-repeatable Read.

Bước demo ĐÃ FIX (chọn "Sau khi xử lý đồng thời"), lặp lại thao tác 1-2:
  - Tab 1 dùng REPEATABLE READ (giữ nguyên snapshot dữ liệu từ đầu
    transaction), nên SoLuong_Lan1 = SoLuong_Lan2 dù Tab 2 đã UPDATE và
    COMMIT thành công ngay giữa 2 lần đọc.


### C.4 PHANTOM READ — Trang "Thống kê thể loại"

Tình huống nghiệp vụ: Cuối ngày, Thủ thư A chạy thống kê đếm số đầu sách
thuộc thể loại "Khoa hoc may tinh" (MaTheLoai=1) hai lần để đối chiếu số
liệu trước khi chốt sổ. Thủ thư B tranh thủ nhập thêm 1 đầu sách mới
đúng thể loại này.

Chuẩn bị: bấm nút "Reset dữ liệu demo" ở đầu trang MỘT LẦN trước khi bắt
đầu (để xoá các sách demo cũ, đảm bảo số liệu ổn định giữa các lần chạy).

Bước demo LỖI (chọn "Trước khi xử lý đồng thời"):
  1. Tab 1: chọn thể loại MaTheLoai=1, bấm "Bắt đầu thống kê" (Thủ thư
     A). Đọc số lượng lần 1 rồi loading khoảng 10 giây.
  2. Trong 10 giây đó, chuyển qua Tab 2: chọn cùng MaTheLoai=1, bấm
     "Nhập sách mới ngay" (Thủ thư B) — thao tác này INSERT 1 dòng mới
     và COMMIT gần như ngay lập tức.
  3. Đợi Tab 1 xong, xem kết quả: SoDong_Lan2 > SoDong_Lan1 — xuất hiện
     1 dòng "bóng ma" trong lần đếm thứ hai dù vẫn trong cùng transaction
     của Thủ thư A.

Bước demo ĐÃ FIX (chọn "Sau khi xử lý đồng thời"):
  1. Bấm lại "Reset dữ liệu demo" trước khi chạy lại.
  2. Lặp lại thao tác 1-2 ở trên.
  3. Điểm khác biệt: Tab 2 (Thủ thư B) lúc này thường sẽ "treo" (loading
     lâu hơn hẳn bình thường, có thể đợi tới khi Tab 1 COMMIT xong mới
     hoàn tất) — vì SERIALIZABLE dùng next-key lock khoá luôn cả khoảng
     giá trị đang được Tab 1 quét qua, không cho Tab 2 INSERT vào giữa
     lúc đó.
  4. Kết quả cuối: SoDong_Lan1 = SoDong_Lan2 (không có bóng ma) — và
     chính việc Tab 2 phải "chờ" là bằng chứng trực quan nhất nên nhấn
     mạnh khi trình bày.


PHẦN D. LƯU Ý KHI TRÌNH BÀY
------------------------------------------------------------------
- Luôn bấm nút "Reset dữ liệu demo" trước khi chạy lại kịch bản Phantom
  Read để tránh số liệu bị lệch do các sách demo cũ còn sót lại.
- Nếu chuyển giữa "Trước khi xử lý đồng thời" và "Sau khi xử lý đồng
  thời", hãy đảm bảo CẢ 2 TAB đều đang ở cùng chế độ trước khi thao
  tác — vì mỗi form ghi nhớ chế độ qua URL (?che_do=truoc / ?che_do=sau)
  tại thời điểm bạn tải lại trang đó.
- Vì các thủ tục lỗi/fix có DO SLEEP(10) hoặc SLEEP(15), mỗi lượt demo
  mất khoảng 10-20 giây là chủ đích, không phải hệ thống bị treo.
- Cuốn sách MaSach=1 ("Ly thuyet Tinh toan") và MaSach=2 ("Nhung nguoi
  khon kho") là 2 cuốn có sẵn trong dữ liệu mẫu ban đầu — dùng chúng cho
  các kịch bản trên là thuận tiện nhất, tránh phải tạo thêm dữ liệu.
