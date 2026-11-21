from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES
from app.modules.auth.repositories._cols import token_columns

# Quy ước trong nguoi_dung: token_bam có giá trị và gui_luc có giá trị = token còn dùng được;
# token_bam có giá trị nhưng gui_luc NULL = token đã được dùng.


def find_account_token_for_update(db: Session, bam_token: bytes, muc_dich: str) -> dict | None:
    token_col, sent_col = token_columns(muc_dich)
    row = db.execute(
        text(f"""
            SELECT id,
                   {sent_col} IS NULL AS da_dung,
                   ({sent_col} + INTERVAL :ttl MINUTE) <= NOW() AS da_het_han
            FROM nguoi_dung
            WHERE {token_col} = :bam_token
            FOR UPDATE
        """),
        {"bam_token": bam_token.hex(), "ttl": AUTH_TOKEN_TTL_MINUTES},
    ).mappings().first()
    if row is None:
        return None
    da_dung = bool(row["da_dung"])
    return {
        "ma_xac_thuc": row["id"],      # Giữ khóa cũ cho service: chính là id người dùng
        "ma_nguoi_dung": row["id"],
        "da_dung_luc": True if da_dung else None,
        "da_het_han": (not da_dung) and bool(row["da_het_han"]),
        "muc_dich": muc_dich,
    }


def mark_token_used(db: Session, ma_xac_thuc: int, muc_dich: str) -> bool:
    token_col, sent_col = token_columns(muc_dich)
    result = db.execute(
        text(f"""
            UPDATE nguoi_dung
            SET {sent_col} = NULL
            WHERE id = :id AND {token_col} IS NOT NULL AND {sent_col} IS NOT NULL
        """),
        {"id": ma_xac_thuc},
    )
    return result.rowcount == 1
