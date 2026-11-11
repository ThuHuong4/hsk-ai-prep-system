from sqlalchemy import text
from sqlalchemy.orm import Session

PUBLISHED = 1  # 0 = Nháp, 1 = Đã xuất bản, 2 = Ẩn/ngừng dùng


def list_exams_by_level(db: Session, ma_cap_do: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT ma_bo_de, ma_cap_do, ten_bo_de, thoi_gian_giay
            FROM bo_de_thi
            WHERE ma_cap_do = :ma_cap_do AND trang_thai = :trang_thai
            ORDER BY ma_bo_de
        """),
        {"ma_cap_do": ma_cap_do, "trang_thai": PUBLISHED},
    ).mappings().all()
    return [dict(row) for row in rows]