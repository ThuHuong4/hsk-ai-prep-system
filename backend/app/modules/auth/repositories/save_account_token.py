from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.auth.repositories._cols import token_columns


def issue_account_token(
    db: Session,
    ma_nguoi_dung: int,
    muc_dich: str,
    bam_token: bytes,
    ttl_minutes: int,  # Hạn được tính khi kiểm tra: thời điểm gửi + ttl (không lưu cột hạn)
) -> None:
    # Ghi đè token cũ: chỉ liên kết mới nhất còn hiệu lực
    token_col, sent_col = token_columns(muc_dich)
    db.execute(
        text(f"""
            UPDATE nguoi_dung
            SET {token_col} = :bam_token, {sent_col} = NOW()
            WHERE id = :ma_nguoi_dung
        """),
        {"ma_nguoi_dung": ma_nguoi_dung, "bam_token": bam_token.hex()},
    )
