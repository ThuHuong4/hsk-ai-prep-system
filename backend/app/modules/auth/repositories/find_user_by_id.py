from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.auth.repositories._cols import USER_COLUMNS


def find_user_by_id(db: Session, ma_nguoi_dung: int) -> dict | None:
    row = db.execute(
        text(f"""
            SELECT {USER_COLUMNS}
            FROM nguoi_dung
            WHERE id = :ma_nguoi_dung
        """),
        {"ma_nguoi_dung": ma_nguoi_dung},
    ).mappings().first()
    return dict(row) if row else None
