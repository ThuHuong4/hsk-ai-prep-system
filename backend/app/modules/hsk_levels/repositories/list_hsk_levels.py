from sqlalchemy import text
from sqlalchemy.orm import Session


def list_hsk_levels(db: Session) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT ma_cap_do, ten_cap_do, mo_ta
            FROM cap_do_hsk
            ORDER BY ma_cap_do
        """)
    ).mappings().all()
    return [dict(row) for row in rows]