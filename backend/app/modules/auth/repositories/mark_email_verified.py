from sqlalchemy import text
from sqlalchemy.orm import Session


def mark_email_verified(db: Session, ma_nguoi_dung: int) -> None:
    db.execute(
        text("""
            UPDATE nguoi_dung
            SET email_xac_minh_luc = NOW(3)
            WHERE ma_nguoi_dung = :ma_nguoi_dung AND email_xac_minh_luc IS NULL
        """),
        {"ma_nguoi_dung": ma_nguoi_dung},
    )