from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.auth.repositories._cols import USER_COLUMNS


def find_user_by_email(db: Session, email: str) -> dict | None:
    row = db.execute(
        text(f"""
            SELECT {USER_COLUMNS}, mat_khau_bam, email_xac_minh_luc
            FROM nguoi_dung
            WHERE email = :email
        """),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None
