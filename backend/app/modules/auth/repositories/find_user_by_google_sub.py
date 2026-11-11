from sqlalchemy import text
from sqlalchemy.orm import Session


def find_user_by_google_sub(db: Session, google_sub: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_nguoi_dung, ho_ten, email, vai_tro, trang_thai
            FROM nguoi_dung
            WHERE google_sub = :google_sub
        """),
        {"google_sub": google_sub},
    ).mappings().first()
    return dict(row) if row else None