import secrets

from sqlalchemy.orm import Session

from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.security.email_identity import normalize_email
from app.security.password_hasher import hash_password, verify_password

ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa

# Hash giả để luôn chạy PBKDF2, kể cả khi email không tồn tại hoặc không có mật khẩu
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


class InvalidCredentialsError(Exception):
    pass


class AccountLockedError(Exception):
    pass


class EmailNotVerifiedError(Exception):
    pass


def authenticate_user(db: Session, email: str, password: str) -> dict:
    user = find_user_by_email(db, normalize_email(email))
    stored_hash = user["mat_khau_bam"] if user and user["mat_khau_bam"] else _DUMMY_HASH
    password_ok = verify_password(password, stored_hash)

    # Không tồn tại, chỉ dùng Google (không có mật khẩu) hoặc sai mật khẩu: cùng một lỗi
    if user is None or not user["mat_khau_bam"] or not password_ok:
        raise InvalidCredentialsError()
    # Chỉ sau khi mật khẩu đúng mới cho biết trạng thái tài khoản
    if user["trang_thai"] != ACTIVE:
        raise AccountLockedError()
    if user["email_xac_minh_luc"] is None:
        raise EmailNotVerifiedError()

    return {
        "ma_nguoi_dung": user["ma_nguoi_dung"],
        "ho_ten": user["ho_ten"],
        "email": user["email"],
        "vai_tro": user["vai_tro"],
    }