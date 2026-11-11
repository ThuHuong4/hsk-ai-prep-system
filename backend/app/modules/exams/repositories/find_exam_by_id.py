from sqlalchemy import text
from sqlalchemy.orm import Session


def find_exam_by_id(db: Session, ma_bo_de: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_bo_de, ma_cap_do, ten_bo_de, thoi_gian_giay,
                   am_thanh_url, trang_thai
            FROM bo_de_thi
            WHERE ma_bo_de = :ma_bo_de
        """),
        {"ma_bo_de": ma_bo_de},
    ).mappings().first()
    return dict(row) if row else None