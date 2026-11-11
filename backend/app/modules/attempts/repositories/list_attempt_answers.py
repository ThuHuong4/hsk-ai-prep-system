from sqlalchemy import text
from sqlalchemy.orm import Session


def list_attempt_answers(db: Session, ma_luot: int) -> list[dict]:
    rows = db.execute(
        text("""
                        SELECT thu_tu, ma_cau_hoi, cau_hoi_chup, cau_tra_loi, danh_dau_xem_lai, phien_ban_luu
            FROM chi_tiet_lam_bai
            WHERE ma_luot = :ma_luot
            ORDER BY thu_tu
        """),
        {"ma_luot": ma_luot},
    ).mappings().all()
    return [dict(row) for row in rows]