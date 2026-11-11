from sqlalchemy.orm import Session

from app.modules.auth.repositories.find_account_token import (
    find_account_token_for_update,
    mark_token_used,
)
from app.modules.auth.repositories.update_password import (
    find_user_for_password_reset,
    update_password_after_reset,
)
from app.security.one_time_token import hash_token, is_well_formed
from app.security.password_hasher import hash_password

PURPOSE = "dat_lai_mat_khau"
ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


class TokenAlreadyUsedError(Exception):
    pass


def reset_password(db: Session, token: str, new_password: str) -> None:
    if not is_well_formed(token):
        raise InvalidTokenError()

    new_hash = hash_password(new_password)  # Băm trước khi khóa dòng để giữ khóa ngắn
    try:
        record = find_account_token_for_update(db, hash_token(token), PURPOSE)
        if record is None:
            raise InvalidTokenError()
        if record["da_dung_luc"] is not None:
            raise TokenAlreadyUsedError()
        if record["da_het_han"]:
            raise ExpiredTokenError()

        user = find_user_for_password_reset(db, record["ma_nguoi_dung"])
        # Tài khoản bị khóa hoặc chỉ dùng Google sau khi cấp token: không cho đặt mật khẩu
        if user is None or user["trang_thai"] != ACTIVE or not user["mat_khau_bam"]:
            raise InvalidTokenError()

        if not mark_token_used(db, record["ma_xac_thuc"]):
            raise TokenAlreadyUsedError()
        update_password_after_reset(db, record["ma_nguoi_dung"], new_hash)
        db.commit()
    except Exception:
        db.rollback()
        raise