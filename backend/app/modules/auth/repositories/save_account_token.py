from sqlalchemy import text
from sqlalchemy.orm import Session


def issue_account_token(
    db: Session,
    ma_nguoi_dung: int,
    muc_dich: str,
    bam_token: bytes,
    ttl_minutes: int,
) -> None:
    # Vô hiệu các token cũ chưa dùng cùng mục đích: chỉ liên kết mới nhất còn hiệu lực
    db.execute(
        text("""
            UPDATE ma_xac_thuc_tai_khoan
            SET het_han_luc = NOW(3)
            WHERE ma_nguoi_dung = :ma_nguoi_dung
              AND muc_dich = :muc_dich
              AND da_dung_luc IS NULL
              AND het_han_luc > NOW(3)
        """),
        {"ma_nguoi_dung": ma_nguoi_dung, "muc_dich": muc_dich},
    )
    db.execute(
        text("""
            INSERT INTO ma_xac_thuc_tai_khoan (ma_nguoi_dung, muc_dich, bam_token, het_han_luc, ngay_tao)
            VALUES (:ma_nguoi_dung, :muc_dich, :bam_token, NOW(3) + INTERVAL :ttl_minutes MINUTE, NOW(3))
        """),
        {
            "ma_nguoi_dung": ma_nguoi_dung,
            "muc_dich": muc_dich,
            "bam_token": bam_token,
            "ttl_minutes": ttl_minutes,
        },
    )