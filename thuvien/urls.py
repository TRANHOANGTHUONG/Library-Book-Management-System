from django.urls import path

from . import views

urlpatterns = [
    path("", views.muon_tra_sach, name="trang_chu"),

    # Các trang nghiệp vụ chính
    path("danh-muc/", views.danh_muc_sach, name="danh_muc_sach"),
    path("tra-cuu-tre-han/", views.tra_cuu_tre_han, name="tra_cuu_tre_han"),
    path("muon-tra-sach/", views.muon_tra_sach, name="muon_tra_sach"),
    path("nghiep-vu/", views.nghiep_vu, name="nghiep_vu"),

    # Các trang thao tác nghiệp vụ có thể mở 2 tab đồng thời
    path("dieu-chinh-kho/", views.dieu_chinh_kho, name="dieu_chinh_kho"),
    path("kiem-tra-nhanh/", views.kiem_tra_nhanh, name="kiem_tra_nhanh"),
    path("xac-nhan-ton-kho/", views.xac_nhan_ton_kho, name="xac_nhan_ton_kho"),
    path("thong-ke-the-loai/", views.thong_ke_the_loai, name="thong_ke_the_loai"),

    # API xử lý form, không trả dữ liệu thô ra giao diện
    path("api/dieu-chinh-kho/", views.api_dieu_chinh_kho, name="api_dieu_chinh_kho"),
    path("api/kiem-tra-nhanh/", views.api_kiem_tra_nhanh, name="api_kiem_tra_nhanh"),
    path("api/xac-nhan-ton-kho/", views.api_xac_nhan_ton_kho, name="api_xac_nhan_ton_kho"),
    path("api/thong-ke-the-loai/", views.api_thong_ke_the_loai, name="api_thong_ke_the_loai"),

    # Trang tổng quan hệ thống
    path("he-thong/", views.dashboard, name="dashboard"),
]