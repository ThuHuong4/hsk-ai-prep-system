from sqlalchemy import text
from sqlalchemy.orm import Session

from app.security.roles import SELF_SIGNUP_ROLE

STUDENT_ROLE = int(SELF_SIGNUP_ROLE)  # Tự đăng ký luôn là Học viên; không nhận vai trò từ client
INITIAL_ENERGY = 5


def _record_initial_energy(db: Session, ma_nguoi_dung: int) -> None:
    # Biến động khởi tạo +5 năng lượng; cùng transaction với việc tạo tài khoản (service commit)
    db.execute(
        text("""
            INSERT INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong)
            VALUES (:id, 'khoi_tao', :so_luong)
        """),
        {"id": ma_nguoi_dung, "so_luong": INITIAL_ENERGY},
    )


def create_student(db: Session, ho_ten: str, email: str, mat_khau_bam: str) -> int:
    """email phải đã được chuẩn hóa; tài khoản mới luôn là Học viên, chưa xác minh email."""
    result = db.execute(
        text("""
            INSERT INTO nguoi_dung (vai_tro_id, email, ho_ten, mat_khau_bam, trang_thai,
                                    email_xac_minh_luc, nang_luong)
            VALUES (:vai_tro, :email, :ho_ten, :mat_khau_bam, 'hoat_dong', NULL, :nang_luong)
        """),
        {
            "vai_tro": STUDENT_ROLE,
            "email": email,
            "ho_ten": ho_ten,
            "mat_khau_bam": mat_khau_bam,
            "nang_luong": INITIAL_ENERGY,
        },
    )
    ma_nguoi_dung = result.lastrowid
    _record_initial_energy(db, ma_nguoi_dung)
    return ma_nguoi_dung


def create_google_student(db: Session, ho_ten: str, email: str, google_sub: str) -> int:
    """Tài khoản tạo từ Google: không có mật khẩu, email đã được Google xác minh."""
    result = db.execute(
        text("""
            INSERT INTO nguoi_dung (vai_tro_id, email, ho_ten, mat_khau_bam, google_sub, trang_thai,
                                    email_xac_minh_luc, nang_luong)
            VALUES (:vai_tro, :email, :ho_ten, NULL, :google_sub, 'hoat_dong', NOW(), :nang_luong)
        """),
        {
            "vai_tro": STUDENT_ROLE,
            "email": email,
            "ho_ten": ho_ten,
            "google_sub": google_sub,
            "nang_luong": INITIAL_ENERGY,
        },
    )
    ma_nguoi_dung = result.lastrowid
    _record_initial_energy(db, ma_nguoi_dung)
    return ma_nguoi_dung
