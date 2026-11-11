from sqlalchemy import text
from sqlalchemy.orm import Session

PUBLISHED = 1  # 0 = Nháp, 1 = Đã xuất bản, 2 = Ẩn/ngừng dùng


def find_published_exam(db: Session, ma_bo_de: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_bo_de, ma_cap_do, ten_bo_de, thoi_gian_giay
            FROM bo_de_thi
            WHERE ma_bo_de = :ma_bo_de AND trang_thai = :trang_thai
        """),
        {"ma_bo_de": ma_bo_de, "trang_thai": PUBLISHED},
    ).mappings().first()
    return dict(row) if row else None