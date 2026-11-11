from sqlalchemy import text
from sqlalchemy.orm import Session
from app.security.roles import SELF_SIGNUP_ROLE
STUDENT_ROLE = int(SELF_SIGNUP_ROLE)  # Tự đăng ký luôn là Học viên; không nhận vai trò từ client
ACTIVE = 1        # trang_thai: 1 = Hoạt động, 0 = Khóa


def create_student(db: Session, ho_ten: str, email: str, mat_khau_bam: str) -> int:
    """email phải đã được chuẩn hóa; tài khoản mới luôn là Học viên, chưa xác minh email."""
    result = db.execute(
        text("""
            INSERT INTO nguoi_dung (ho_ten, email, mat_khau_bam, vai_tro, trang_thai, email_xac_minh_luc)
            VALUES (:ho_ten, :email, :mat_khau_bam, :vai_tro, :trang_thai, NULL)
        """),
        {
            "ho_ten": ho_ten,
            "email": email,
            "mat_khau_bam": mat_khau_bam,
            "vai_tro": STUDENT_ROLE,
            "trang_thai": ACTIVE,
        },
    )
    return result.lastrowid
def create_google_student(db: Session, ho_ten: str, email: str, google_sub: str) -> int:
    """Tài khoản tạo từ Google: không có mật khẩu, email đã được Google xác minh."""
    result = db.execute(
        text("""
            INSERT INTO nguoi_dung (ho_ten, email, mat_khau_bam, vai_tro, trang_thai,
                                    google_sub, email_xac_minh_luc)
            VALUES (:ho_ten, :email, NULL, :vai_tro, :trang_thai, :google_sub, NOW(3))
        """),
        {
            "ho_ten": ho_ten,
            "email": email,
            "vai_tro": STUDENT_ROLE,
            "trang_thai": ACTIVE,
            "google_sub": google_sub,
        },
    )
    return result.lastrowid