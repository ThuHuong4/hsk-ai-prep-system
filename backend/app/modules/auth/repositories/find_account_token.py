from sqlalchemy import text
from sqlalchemy.orm import Session


def find_account_token_for_update(db: Session, bam_token: bytes, muc_dich: str) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_xac_thuc, ma_nguoi_dung, het_han_luc, da_dung_luc
            FROM ma_xac_thuc_tai_khoan
            WHERE bam_token = :bam_token AND muc_dich = :muc_dich
            FOR UPDATE
        """),
        {"bam_token": bam_token, "muc_dich": muc_dich},
    ).mappings().first()
    if row is None:
        return None

    # Lấy giờ MySQL bằng câu lệnh riêng, sau khi đã có khóa
    now = db.execute(text("SELECT NOW(3)")).scalar_one()
    record = dict(row)
    record["da_het_han"] = record["het_han_luc"] <= now
    return record


def mark_token_used(db: Session, ma_xac_thuc: int) -> bool:
    result = db.execute(
        text("""
            UPDATE ma_xac_thuc_tai_khoan
            SET da_dung_luc = NOW(3)
            WHERE ma_xac_thuc = :ma_xac_thuc AND da_dung_luc IS NULL
        """),
        {"ma_xac_thuc": ma_xac_thuc},
    )
    return result.rowcount == 1