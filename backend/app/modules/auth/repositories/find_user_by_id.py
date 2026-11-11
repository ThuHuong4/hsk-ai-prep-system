from sqlalchemy import text
from sqlalchemy.orm import Session


def find_user_by_id(db: Session, ma_nguoi_dung: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_nguoi_dung, ho_ten, email, vai_tro, trang_thai
            FROM nguoi_dung
            WHERE ma_nguoi_dung = :ma_nguoi_dung
        """),
        {"ma_nguoi_dung": ma_nguoi_dung},
    ).mappings().first()
    return dict(row) if row else None