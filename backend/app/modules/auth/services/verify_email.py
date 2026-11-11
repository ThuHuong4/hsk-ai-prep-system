from sqlalchemy.orm import Session

from app.modules.auth.repositories.find_account_token import (
    find_account_token_for_update,
    mark_token_used,
)
from app.modules.auth.repositories.mark_email_verified import mark_email_verified
from app.security.one_time_token import hash_token, is_well_formed

PURPOSE = "xac_minh_email"


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


class TokenAlreadyUsedError(Exception):
    pass


def verify_email(db: Session, token: str) -> None:
    if not is_well_formed(token):
        raise InvalidTokenError()
    try:
        record = find_account_token_for_update(db, hash_token(token), PURPOSE)
        if record is None:
            raise InvalidTokenError()
        if record["da_dung_luc"] is not None:
            raise TokenAlreadyUsedError()
        if record["da_het_han"]:
            raise ExpiredTokenError()
        if not mark_token_used(db, record["ma_xac_thuc"]):
            raise TokenAlreadyUsedError()
        mark_email_verified(db, record["ma_nguoi_dung"])
        db.commit()
    except Exception:
        db.rollback()
        raise