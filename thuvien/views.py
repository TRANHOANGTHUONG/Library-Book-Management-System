import time
from datetime import date

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from . import db


# ==================================================================
# HAM DUNG CHUNG
# ==================================================================

def _timed_call(proc_name, params=None):
    params = params or []
    t0 = time.time()
    result = db.call_procedure(proc_name, params)
    result["thoi_gian_giay"] = round(time.time() - t0, 2)
    return result


def _to_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} không hợp lệ.")


def _safe_error_message(error):
    raw = str(error)

    known_errors = {
        "So luong sach khong duoc am": "Số lượng sách không được âm.",
        "Sach da het trong kho": "Sách đã hết trong kho.",
        "Ma the loai khong ton tai": "Mã thể loại không tồn tại.",
        "Khong tim thay": "Không tìm thấy dữ liệu phù hợp.",
        "Lock wait timeout": "Dữ liệu đang được xử lý bởi thao tác khác. Vui lòng thử lại.",
        "Deadlock": "Dữ liệu đang được xử lý đồng thời. Vui lòng thử lại.",
    }

    for key, message in known_errors.items():
        if key.lower() in raw.lower():
            return message

    return "Không thể hoàn tất thao tác. Vui lòng kiểm tra lại thông tin nhập."


def _first_value(row, *names):
    if not row:
        return None

    for name in names:
        if name in row:
            return row[name]

    return None


def _call_proc_or_raise(proc_name, params=None):
    result = _timed_call(proc_name, params or [])

    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Không thể hoàn tất thao tác."))

    return result.get("rows", []), result.get("thoi_gian_giay")


def _json_success(message, **extra):
    payload = {
        "success": True,
        "message": message,
    }
    payload.update(extra)
    return JsonResponse(payload)


def _json_error(error):
    return JsonResponse(
        {
            "success": False,
            "message": _safe_error_message(error),
        },
        status=400,
    )


def _is_controlled_mode(post_data):
    """
    Ho tro dong thoi ten cu va ten moi:
    - che_do=sau
    - phuong_thuc=kiem_soat / xac_nhan / on_dinh
    """
    che_do = post_data.get("che_do")
    phuong_thuc = post_data.get("phuong_thuc")

    return che_do == "sau" or phuong_thuc in {
        "kiem_soat",
        "xac_nhan",
        "on_dinh",
    }

def _get_the_loai_info(ma_theloai):
    rows = db.run_select(
        """
        SELECT MaTheLoai, TenTheLoai
        FROM TheLoai
        WHERE MaTheLoai = %s
        LIMIT 1
        """,
        [ma_theloai],
    )

    if not rows:
        raise ValueError("Mã thể loại không tồn tại.")

    return rows[0]

# ==================================================================
# TRANG CHU / DASHBOARD
# ==================================================================

def dashboard(request):
    """
    Trang tổng quan kỹ thuật không còn đẩy danh sách bảng, view,
    procedure, trigger ra giao diện người dùng.
    """
    cards = [
        {
            "title": "Danh mục sách",
            "description": "Tra cứu thông tin sách trong thư viện.",
            "url_name": "danh_muc_sach",
        },
        {
            "title": "Mượn / Trả sách",
            "description": "Lập phiếu mượn và xử lý trả sách.",
            "url_name": "muon_tra_sach",
        },
        {
            "title": "Nghiệp vụ thư viện",
            "description": "Thêm sách mới và thanh toán phiếu phạt.",
            "url_name": "nghiep_vu",
        },
        {
            "title": "Điều chỉnh tồn kho",
            "description": "Cập nhật số lượng sách trong kho.",
            "url_name": "dieu_chinh_kho",
        },
        {
            "title": "Tra cứu số lượng",
            "description": "Tra cứu nhanh số lượng sách.",
            "url_name": "kiem_tra_nhanh",
        },
        {
            "title": "Xác nhận tồn kho",
            "description": "Kiểm tra số lượng sách trước khi xử lý.",
            "url_name": "xac_nhan_ton_kho",
        },
        {
            "title": "Thống kê thể loại",
            "description": "Thống kê số đầu sách theo thể loại.",
            "url_name": "thong_ke_the_loai",
        },
    ]

    return render(request, "thuvien/dashboard.html", {"cards": cards})


# ==================================================================
# 1) DANH MUC SACH
# ==================================================================

DANH_MUC_OPTIONS = [
    ("vw_DanhMucSach", "Danh mục sách đầy đủ"),
    ("vw_LichSuMuonSach", "Lịch sử mượn sách"),
    ("vw_SachDangMuon", "Sách đang được mượn"),
    ("vw_TopSachYeuThich", "Sách được mượn nhiều nhất"),
    ("vw_DocGiaTreHan", "Độc giả đang trễ hạn trả sách"),
]

_DANH_MUC_MAP = dict(DANH_MUC_OPTIONS)


def danh_muc_sach(request):
    selected = request.GET.get("muc", DANH_MUC_OPTIONS[0][0])

    if selected not in _DANH_MUC_MAP:
        selected = DANH_MUC_OPTIONS[0][0]

    rows = db.run_select(f"SELECT * FROM {selected} LIMIT 100")

    context = {
        "options": DANH_MUC_OPTIONS,
        "selected": selected,
        "selected_label": _DANH_MUC_MAP[selected],
        "rows": rows,
        "columns": list(rows[0].keys()) if rows else [],
    }

    return render(request, "thuvien/danh_muc_sach.html", context)


# ==================================================================
# 2) TRA CUU TRE HAN
# ==================================================================

def tra_cuu_tre_han(request):
    result = None
    han_tra = request.GET.get("han_tra", "")
    ngay_tra = request.GET.get("ngay_tra", "")

    if han_tra:
        result = db.run_scalar_function(
            "SELECT fn_SoNgayTreHan(%s, %s)",
            [han_tra, ngay_tra or None],
        )

    return render(
        request,
        "thuvien/tra_cuu_tre_han.html",
        {
            "han_tra": han_tra,
            "ngay_tra": ngay_tra,
            "result": result,
        },
    )


# ==================================================================
# 3) MUON / TRA SACH
# ==================================================================

def muon_tra_sach(request):
    message, error = None, None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "muon":
            result = db.call_procedure(
                "sp_LapPhieuMuon",
                [
                    request.POST.get("ma_docgia"),
                    date.today().isoformat(),
                    request.POST.get("han_tra"),
                    request.POST.get("ma_sach"),
                ],
            )

            if result.get("ok"):
                message = "Lập phiếu mượn thành công."
            else:
                error = _safe_error_message(result.get("error"))

        elif action == "tra":
            result = db.call_procedure(
                "sp_TraSach_VaXuLyPhat",
                [
                    request.POST.get("ma_phieu"),
                    request.POST.get("ma_sach"),
                    request.POST.get("tinh_trang", "Binh thuong"),
                ],
            )

            if result.get("ok"):
                message = "Xử lý trả sách thành công."
            else:
                error = _safe_error_message(result.get("error"))

        else:
            error = "Hành động không hợp lệ."

    sach = db.run_select(
        """
        SELECT MaSach, TenSach, SoLuong
        FROM Sach
        ORDER BY MaSach
        """
    )

    dang_muon = db.run_select(
        """
        SELECT ct.MaPhieu, ct.MaSach, s.TenSach, pm.MaDocGia
        FROM ChiTietPhieuMuon ct
        JOIN Sach s ON s.MaSach = ct.MaSach
        JOIN PhieuMuon pm ON pm.MaPhieu = ct.MaPhieu
        WHERE ct.NgayTraThucTe IS NULL
        ORDER BY ct.MaPhieu DESC
        LIMIT 20
        """
    )

    docgia = db.run_select(
        """
        SELECT MaDocGia, HoTen
        FROM DocGia
        ORDER BY MaDocGia
        """
    )

    return render(
        request,
        "thuvien/muon_tra_sach.html",
        {
            "sach": sach,
            "dang_muon": dang_muon,
            "docgia": docgia,
            "message": message,
            "error": error,
        },
    )


# ==================================================================
# 4) NGHIEP VU THU VIEN
# ==================================================================

def nghiep_vu(request):
    message, error = None, None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "them_sach":
            result = db.call_procedure(
                "sp_ThemSachMoi",
                [
                    request.POST.get("ten_sach"),
                    request.POST.get("nam_xb") or None,
                    request.POST.get("so_luong"),
                    request.POST.get("ma_theloai"),
                ],
            )

            if result.get("ok"):
                message = "Thêm sách mới thành công."
            else:
                error = _safe_error_message(result.get("error"))

        elif action == "thanh_toan":
            result = db.call_procedure(
                "sp_ThanhToanPhat",
                [
                    request.POST.get("ma_phieuphat"),
                    request.POST.get("so_tien"),
                ],
            )

            if result.get("ok"):
                message = "Thanh toán phiếu phạt thành công."
            else:
                error = _safe_error_message(result.get("error"))

        else:
            error = "Hành động không hợp lệ."

    theloai = db.run_select(
        """
        SELECT MaTheLoai, TenTheLoai
        FROM TheLoai
        ORDER BY MaTheLoai
        """
    )

    phieuphat = db.run_select(
        """
        SELECT MaPhieuPhat, LyDo, SoTienPhat, TrangThai
        FROM PhieuPhat
        WHERE TrangThai = 'Chua thanh toan'
        ORDER BY MaPhieuPhat
        """
    )

    return render(
        request,
        "thuvien/nghiep_vu.html",
        {
            "theloai": theloai,
            "phieuphat": phieuphat,
            "message": message,
            "error": error,
        },
    )


# ==================================================================
# 5) CAC TRANG THAO TAC DONG THOI
#    Giao dien chi con 1 form.
#    Nguoi dung mo 2 tab cung mot trang de thao tac dong thoi.
# ==================================================================

def dieu_chinh_kho(request):
    """
    Trang điều chỉnh tồn kho.
    Không còn chia Thủ thư A/B.
    """
    return render(
        request,
        "thuvien/dieu_chinh_kho.html",
        {
            "che_do": request.GET.get("che_do", "truoc"),
            "message": None,
            "error": None,
        },
    )


def kiem_tra_nhanh(request):
    """
    Trang tra cứu số lượng sách.
    Không còn chia Thủ thư A/B.
    """
    return render(
        request,
        "thuvien/kiem_tra_nhanh.html",
        {
            "che_do": request.GET.get("che_do", "truoc"),
            "message": None,
            "error": None,
        },
    )


def xac_nhan_ton_kho(request):
    """
    Trang xác nhận tồn kho.
    Không còn chia Thủ thư A/B.
    """
    return render(
        request,
        "thuvien/xac_nhan_ton_kho.html",
        {
            "che_do": request.GET.get("che_do", "truoc"),
            "message": None,
            "error": None,
        },
    )


def thong_ke_the_loai(request):

    theloai = db.run_select(
        """
        SELECT MaTheLoai, TenTheLoai
        FROM TheLoai
        ORDER BY MaTheLoai
        """
    )

    return render(
        request,
        "thuvien/thong_ke_the_loai.html",
        {
            "che_do": request.GET.get("che_do", "truoc"),
            "theloai": theloai,
            "message": None,
            "error": None,
        },
    )

# ==================================================================
# 6) API CHO CAC TRANG THAO TAC DONG THOI
#    Tra JSON sach, khong tra rows/debug data.
# ==================================================================

@require_POST
def api_dieu_chinh_kho(request):
    try:
        ma_sach = _to_int(request.POST.get("ma_sach"), "Mã sách")
        delta = _to_int(
            request.POST.get("delta_qty") or request.POST.get("delta"),
            "Số lượng điều chỉnh",
        )

        proc_name = (
            "sp_CapNhatSoLuong_PESSIMISTIC"
            if _is_controlled_mode(request.POST)
            else "sp_CapNhatSoLuong_LOSTUPDATE"
        )

        rows, thoi_gian = _call_proc_or_raise(proc_name, [ma_sach, delta])
        row = rows[0] if rows else {}

        so_luong = _first_value(row, "SoLuong_DaGhi", "SoLuong")

        return _json_success(
            "Điều chỉnh tồn kho thành công.",
            ma_sach=ma_sach,
            so_luong=so_luong,
            thoi_gian=thoi_gian,
        )

    except Exception as error:
        return _json_error(error)


@require_POST
def api_kiem_tra_nhanh(request):
    try:
        cong_viec = request.POST.get("cong_viec")

        if not cong_viec:
            vai_tro = request.POST.get("vai_tro")
            cong_viec = "hieu_chinh" if vai_tro == "a" else "tra_cuu"

        ma_sach = _to_int(request.POST.get("ma_sach"), "Mã sách")

        if cong_viec == "hieu_chinh":
            so_luong_nhap = _to_int(
                request.POST.get("so_luong_nhap")
                or request.POST.get("so_luong_nham"),
                "Số lượng ghi nhận",
            )

            _, thoi_gian = _call_proc_or_raise(
                "sp_TaoDuLieuRac_DIRTYREAD",
                [ma_sach, so_luong_nhap],
            )

            return _json_success(
                "Phiên kiểm kê đã kết thúc.",
                ma_sach=ma_sach,
                thoi_gian=thoi_gian,
            )

        proc_name = (
            "sp_DocDuLieuAnToan_READCOMMITTED"
            if _is_controlled_mode(request.POST)
            else "sp_DocDuLieuRac_DIRTYREAD"
        )

        rows, thoi_gian = _call_proc_or_raise(proc_name, [ma_sach])
        row = rows[0] if rows else {}

        so_luong = _first_value(
            row,
            "SoLuong_DocDuoc_AnToan",
            "SoLuong_DocDuoc_Rac",
            "SoLuong",
        )

        return _json_success(
            "Tra cứu số lượng sách hoàn tất.",
            ma_sach=ma_sach,
            so_luong=so_luong,
            thoi_gian=thoi_gian,
        )

    except Exception as error:
        return _json_error(error)


@require_POST
def api_xac_nhan_ton_kho(request):
    try:
        cong_viec = request.POST.get("cong_viec")

        if not cong_viec:
            vai_tro = request.POST.get("vai_tro")
            cong_viec = "kiem_tra" if vai_tro == "a" else "cap_nhat"

        ma_sach = _to_int(request.POST.get("ma_sach"), "Mã sách")

        if cong_viec == "cap_nhat":
            so_luong_moi = _to_int(
                request.POST.get("so_luong_moi"),
                "Số lượng mới",
            )

            _, thoi_gian = _call_proc_or_raise(
                "sp_CapNhat_NONREPEATABLE",
                [ma_sach, so_luong_moi],
            )

            return _json_success(
                "Cập nhật thông tin sách thành công.",
                ma_sach=ma_sach,
                so_luong=so_luong_moi,
                thoi_gian=thoi_gian,
            )

        proc_name = (
            "sp_DocHaiLan_NONREPEATABLE_FIX"
            if _is_controlled_mode(request.POST)
            else "sp_DocHaiLan_NONREPEATABLE_BUG"
        )

        rows, thoi_gian = _call_proc_or_raise(proc_name, [ma_sach])
        row = rows[0] if rows else {}

        lan_1 = _first_value(row, "SoLuong_Lan1")
        lan_2 = _first_value(row, "SoLuong_Lan2")

        trang_thai = "Dữ liệu ổn định"

        if lan_1 is not None and lan_2 is not None and lan_1 != lan_2:
            trang_thai = "Dữ liệu đã thay đổi trong quá trình kiểm tra"

        return _json_success(
            "Xác nhận tồn kho hoàn tất.",
            ma_sach=ma_sach,
            so_luong=lan_2,
            so_luong_xac_nhan_dau=lan_1,
            so_luong_xac_nhan_sau=lan_2,
            trang_thai=trang_thai,
            thoi_gian=thoi_gian,
        )

    except Exception as error:
        return _json_error(error)


@require_POST
def api_thong_ke_the_loai(request):
    try:
        cong_viec = request.POST.get("cong_viec")

        if not cong_viec:
            vai_tro = request.POST.get("vai_tro")
            if vai_tro == "reset":
                cong_viec = "lam_moi"
            elif vai_tro == "a":
                cong_viec = "thong_ke"
            else:
                cong_viec = "bo_sung"

        if cong_viec == "lam_moi":
            ma_theloai = 1
            the_loai_info = _get_the_loai_info(ma_theloai)

            rows, thoi_gian = _call_proc_or_raise("sp_Reset_PHANTOM_DEMO", [])
            row = rows[0] if rows else {}

            so_dau_sach = _first_value(
                row,
                "SoSach_TheLoai_1_HienTai",
                "SoDong_Lan2",
                "SoDong_Lan1",
            )

            return _json_success(
                "Dữ liệu thống kê đã được làm mới.",
                ma_the_loai=the_loai_info["MaTheLoai"],
                ten_the_loai=the_loai_info["TenTheLoai"],
                so_dau_sach=so_dau_sach,
                thoi_gian=thoi_gian,
            )

        ma_theloai = _to_int(
            request.POST.get("ma_the_loai") or request.POST.get("ma_theloai"),
            "Mã thể loại",
        )

        the_loai_info = _get_the_loai_info(ma_theloai)

        if cong_viec == "bo_sung":
            proc_name = (
                "sp_ThemSach_PHANTOM_FIX"
                if _is_controlled_mode(request.POST)
                else "sp_ThemSach_PHANTOM_BUG"
            )

            _, thoi_gian = _call_proc_or_raise(proc_name, [ma_theloai])

            return _json_success(
                "Bổ sung đầu sách vào danh mục thành công.",
                ma_the_loai=the_loai_info["MaTheLoai"],
                ten_the_loai=the_loai_info["TenTheLoai"],
                thoi_gian=thoi_gian,
            )

        proc_name = (
            "sp_DemSach_PHANTOM_FIX"
            if _is_controlled_mode(request.POST)
            else "sp_DemSach_PHANTOM_BUG"
        )

        rows, thoi_gian = _call_proc_or_raise(proc_name, [ma_theloai])
        row = rows[0] if rows else {}

        so_dau_sach_lan_1 = _first_value(row, "SoDong_Lan1")
        so_dau_sach_lan_2 = _first_value(row, "SoDong_Lan2")
        so_dau_sach = _first_value(row, "SoDong_Lan2", "SoDong_Lan1")

        if so_dau_sach_lan_1 is not None and so_dau_sach_lan_2 is not None:
            if so_dau_sach_lan_1 != so_dau_sach_lan_2:
                trang_thai = "Số đầu sách thay đổi trong quá trình thống kê."
            else:
                trang_thai = "Số đầu sách ổn định trong quá trình thống kê."
        else:
            trang_thai = None

        return _json_success(
            "Thống kê thể loại hoàn tất.",
            ma_the_loai=the_loai_info["MaTheLoai"],
            ten_the_loai=the_loai_info["TenTheLoai"],
            so_dau_sach=so_dau_sach,
            so_dau_sach_lan_1=so_dau_sach_lan_1,
            so_dau_sach_lan_2=so_dau_sach_lan_2,
            trang_thai=trang_thai,
            thoi_gian=thoi_gian,
        )

    except Exception as error:
        return _json_error(error)