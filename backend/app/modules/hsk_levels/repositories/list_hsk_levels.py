from sqlalchemy import text
from sqlalchemy.orm import Session


def list_hsk_levels(db: Session) -> list[dict]:
    # Bảng cap_do của CSDL Xianglingo; giữ tên trường cũ cho frontend
    rows = db.execute(
        text("""
            SELECT id AS ma_cap_do, ten AS ten_cap_do, NULL AS mo_ta
            FROM cap_do
            WHERE trang_thai = 'da_dang'
            ORDER BY thu_tu
        """)
    ).mappings().all()
    return [dict(row) for row in rows]
