from sqlalchemy import text
from sqlalchemy.orm import Session

EXAM_ATTEMPT = 2  # luot_hoc.loai_luot: 2 = Thi thử
IN_PROGRESS = 0   # luot_hoc.trang_thai: 0 = Đang làm
NOT_GRADED = 0    # chi_tiet_lam_bai.trang_thai_cham: 0 = Chưa chấm


def create_exam_attempt(
    db: Session,
    ma_nguoi_dung: int,
    ma_cap_do: int,
    ma_bo_de: int,
    thoi_gian_giay: int,
    cau_hinh_chup: str,
    chi_tiet: list[dict],
) -> int:
    """chi_tiet: mỗi phần tử gồm ma_cau_hoi, ma_ky_nang, ma_dang, thu_tu,
    phien_ban_cau_hoi, bam_noi_dung (32 byte), cau_hoi_chup (JSON), diem_toi_da."""
    if not chi_tiet:
        raise ValueError("Đề thi không có câu hỏi")

    result = db.execute(
        text("""
            INSERT INTO luot_hoc (
                ma_nguoi_dung, ma_cap_do, ma_bo_de, loai_luot, trang_thai,
                bat_dau_luc, han_nop_luc, tong_so_cau, so_cau_chua_cham, cau_hinh_chup
            ) VALUES (
                :ma_nguoi_dung, :ma_cap_do, :ma_bo_de, :loai_luot, :trang_thai,
                NOW(3), NOW(3) + INTERVAL :thoi_gian_giay SECOND,
                :tong_so_cau, :tong_so_cau, :cau_hinh_chup
            )
        """),
        {
            "ma_nguoi_dung": ma_nguoi_dung,
            "ma_cap_do": ma_cap_do,
            "ma_bo_de": ma_bo_de,
            "loai_luot": EXAM_ATTEMPT,
            "trang_thai": IN_PROGRESS,
            "thoi_gian_giay": thoi_gian_giay,
            "tong_so_cau": len(chi_tiet),
            "cau_hinh_chup": cau_hinh_chup,
        },
    )
    ma_luot = result.lastrowid

    db.execute(
        text("""
            INSERT INTO chi_tiet_lam_bai (
                ma_luot, ma_cau_hoi, ma_ky_nang, ma_dang, thu_tu,
                phien_ban_cau_hoi, bam_noi_dung, cau_hoi_chup,
                trang_thai_cham, diem_toi_da
            ) VALUES (
                :ma_luot, :ma_cau_hoi, :ma_ky_nang, :ma_dang, :thu_tu,
                :phien_ban_cau_hoi, :bam_noi_dung, :cau_hoi_chup,
                :trang_thai_cham, :diem_toi_da
            )
        """),
        [{**row, "ma_luot": ma_luot, "trang_thai_cham": NOT_GRADED} for row in chi_tiet],
    )
    return ma_luot