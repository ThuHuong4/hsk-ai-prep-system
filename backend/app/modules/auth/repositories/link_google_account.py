from sqlalchemy import text
from sqlalchemy.orm import Session


def find_user_for_google_link(db: Session, email: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_nguoi_dung, ho_ten, email, vai_tro, trang_thai, mat_khau_bam, google_sub
            FROM nguoi_dung
            WHERE email = :email
            FOR UPDATE
        """),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def link_google_sub(db: Session, ma_nguoi_dung: int, google_sub: str) -> bool:
    # Chỉ gắn khi tài khoản chưa có Google; Google đã xác minh email nên đánh dấu nếu chưa có
    result = db.execute(
        text("""
            UPDATE nguoi_dung
            SET google_sub = :google_sub,
                email_xac_minh_luc = COALESCE(email_xac_minh_luc, NOW(3))
            WHERE ma_nguoi_dung = :ma_nguoi_dung AND google_sub IS NULL
        """),
        {"ma_nguoi_dung": ma_nguoi_dung, "google_sub": google_sub},
    )
    return result.rowcount == 1