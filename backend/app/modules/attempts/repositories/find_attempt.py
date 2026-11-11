from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

EXAM_ATTEMPT = 2  # luot_hoc.loai_luot: 2 = Thi thử
IN_PROGRESS = 0   # luot_hoc.trang_thai: 0 = Đang làm


def _db_now(db: Session) -> datetime:
    return db.execute(text("SELECT NOW(3)")).scalar_one()


def _add_remaining_time(db: Session, attempt: dict) -> dict:
    # Lấy giờ MySQL bằng câu lệnh riêng, sau khi đã có khóa
    now = _db_now(db)
    attempt["da_het_han"] = attempt["han_nop_luc"] <= now
    attempt["con_lai_giay"] = max(0, int((attempt["han_nop_luc"] - now).total_seconds()))
    return attempt


def lock_user(db: Session, ma_nguoi_dung: int) -> bool:
    row = db.execute(
        text("""
            SELECT ma_nguoi_dung
            FROM nguoi_dung
            WHERE ma_nguoi_dung = :ma_nguoi_dung
            FOR UPDATE
        """),
        {"ma_nguoi_dung": ma_nguoi_dung},
    ).first()
    return row is not None


def find_active_exam_attempt(db: Session, ma_nguoi_dung: int, ma_bo_de: int) -> dict | None:
    # FOR UPDATE để đọc dữ liệu mới nhất đã commit, không đọc snapshot cũ của transaction
    row = db.execute(
        text("""
            SELECT ma_luot, ma_bo_de, ma_cap_do, bat_dau_luc, han_nop_luc,
                   tong_so_cau, cau_hinh_chup
            FROM luot_hoc
            WHERE ma_nguoi_dung = :ma_nguoi_dung
              AND ma_bo_de = :ma_bo_de
              AND loai_luot = :loai_luot
              AND trang_thai = :trang_thai
            ORDER BY ma_luot DESC
            LIMIT 1
            FOR UPDATE
        """),
        {
            "ma_nguoi_dung": ma_nguoi_dung,
            "ma_bo_de": ma_bo_de,
            "loai_luot": EXAM_ATTEMPT,
            "trang_thai": IN_PROGRESS,
        },
    ).mappings().first()
    return _add_remaining_time(db, dict(row)) if row else None


def lock_exam_attempt_for_user(db: Session, ma_luot: int, ma_nguoi_dung: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_luot, trang_thai, han_nop_luc
            FROM luot_hoc
            WHERE ma_luot = :ma_luot
              AND ma_nguoi_dung = :ma_nguoi_dung
              AND loai_luot = :loai_luot
            FOR UPDATE
        """),
        {"ma_luot": ma_luot, "ma_nguoi_dung": ma_nguoi_dung, "loai_luot": EXAM_ATTEMPT},
    ).mappings().first()
    return _add_remaining_time(db, dict(row)) if row else None