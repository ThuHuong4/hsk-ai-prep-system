from sqlalchemy import text
from sqlalchemy.orm import Session


def find_user_by_email(db: Session, email: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_nguoi_dung, ho_ten, email, mat_khau_bam, vai_tro, trang_thai,email_xac_minh_luc
            FROM nguoi_dung
            WHERE email = :email
        """),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None