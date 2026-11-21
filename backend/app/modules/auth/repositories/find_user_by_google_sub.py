from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.auth.repositories._cols import USER_COLUMNS


def find_user_by_google_sub(db: Session, google_sub: str) -> dict | None:
    row = db.execute(
        text(f"""
            SELECT {USER_COLUMNS}
            FROM nguoi_dung
            WHERE google_sub = :google_sub
        """),
        {"google_sub": google_sub},
    ).mappings().first()
    return dict(row) if row else None
