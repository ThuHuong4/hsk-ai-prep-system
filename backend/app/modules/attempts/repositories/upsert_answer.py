from sqlalchemy import text
from sqlalchemy.orm import Session


def find_answer_for_update(db: Session, ma_luot: int, ma_cau_hoi: int) -> dict | None:
    # FOR UPDATE để đọc bản mới nhất đã commit, không đọc snapshot cũ của transaction
    row = db.execute(
        text("""
            SELECT ma_chi_tiet, cau_hoi_chup, cau_tra_loi, danh_dau_xem_lai, phien_ban_luu
            FROM chi_tiet_lam_bai
            WHERE ma_luot = :ma_luot AND ma_cau_hoi = :ma_cau_hoi
            FOR UPDATE
        """),
        {"ma_luot": ma_luot, "ma_cau_hoi": ma_cau_hoi},
    ).mappings().first()
    return dict(row) if row else None


def update_answer(
    db: Session,
    ma_chi_tiet: int,
    cau_tra_loi: str | None,
    danh_dau_xem_lai: bool,
    phien_ban_luu: int,
) -> None:
    db.execute(
        text("""
            UPDATE chi_tiet_lam_bai
            SET cau_tra_loi = :cau_tra_loi,
                danh_dau_xem_lai = :danh_dau_xem_lai,
                phien_ban_luu = :phien_ban_luu
            WHERE ma_chi_tiet = :ma_chi_tiet
        """),
        {
            "ma_chi_tiet": ma_chi_tiet,
            "cau_tra_loi": cau_tra_loi,
            "danh_dau_xem_lai": 1 if danh_dau_xem_lai else 0,
            "phien_ban_luu": phien_ban_luu,
        },
    )


def increment_attempt_save_version(db: Session, ma_luot: int) -> None:
    db.execute(
        text("UPDATE luot_hoc SET phien_ban_luu = phien_ban_luu + 1 WHERE ma_luot = :ma_luot"),
        {"ma_luot": ma_luot},
    )