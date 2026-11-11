from sqlalchemy import text
from sqlalchemy.orm import Session


def find_user_for_password_reset(db: Session, ma_nguoi_dung: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_nguoi_dung, trang_thai, mat_khau_bam
            FROM nguoi_dung
            WHERE ma_nguoi_dung = :ma_nguoi_dung
            FOR UPDATE
        """),
        {"ma_nguoi_dung": ma_nguoi_dung},
    ).mappings().first()
    return dict(row) if row else None


def update_password_after_reset(db: Session, ma_nguoi_dung: int, mat_khau_bam: str) -> None:
    # Mở được liên kết trong hộp thư = chứng minh sở hữu email -> đánh dấu đã xác minh nếu chưa có
    db.execute(
        text("""
            UPDATE nguoi_dung
            SET mat_khau_bam = :mat_khau_bam,
                email_xac_minh_luc = COALESCE(email_xac_minh_luc, NOW(3))
            WHERE ma_nguoi_dung = :ma_nguoi_dung
        """),
        {"ma_nguoi_dung": ma_nguoi_dung, "mat_khau_bam": mat_khau_bam},
    )