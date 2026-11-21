# Ánh xạ CSDL Xianglingo (bảng nguoi_dung) sang tên trường cũ mà các service đang dùng.
# trang_thai: 'hoat_dong' -> 1, 'khoa' -> 0 để giữ nguyên logic ACTIVE = 1 ở service.
USER_COLUMNS = """
    id AS ma_nguoi_dung, ho_ten, email, vai_tro_id AS vai_tro,
    CASE trang_thai WHEN 'hoat_dong' THEN 1 ELSE 0 END AS trang_thai,
    (email_xac_minh_luc IS NOT NULL) AS email_da_xac_minh
"""

# Cột token theo mục đích (token nằm ngay trong nguoi_dung)
TOKEN_COLUMNS = {
    "xac_minh_email": ("xm_token_bam", "xm_gui_luc"),
    "dat_lai_mat_khau": ("dl_token_bam", "dl_gui_luc"),
}


def token_columns(muc_dich: str) -> tuple[str, str]:
    try:
        return TOKEN_COLUMNS[muc_dich]
    except KeyError:
        raise ValueError("Mục đích token không hợp lệ") from None
