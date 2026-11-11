from app.database.integrity import is_duplicate_key
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_config import (
    AUTH_LINK_LIMIT_PER_EMAIL_PER_HOUR,
    AUTH_LINK_LIMIT_PER_IP_PER_HOUR,
)
from app.modules.auth.repositories.find_user_by_google_sub import find_user_by_google_sub
from app.modules.auth.repositories.link_google_account import (
    find_user_for_google_link,
    link_google_sub,
)
from app.modules.auth.services.authenticate_user import (
    _DUMMY_HASH,
    AccountLockedError,
    InvalidCredentialsError,
)
from app.modules.auth.services.enforce_request_limit import check_and_record_request
from app.modules.auth.services.login_with_google import GoogleEmailNotVerifiedError
from app.security.email_identity import normalize_email
from app.security.password_hasher import verify_password

ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa
PURPOSE = "lien_ket_google"


class GoogleAlreadyLinkedError(Exception):
    """Tài khoản Google này đã gắn với một tài khoản HSK AI."""


class AccountAlreadyHasGoogleError(Exception):
    """Tài khoản HSK AI này đã gắn với một tài khoản Google khác."""


def link_google_account(db: Session, identity: dict, password: str, dia_chi_ip: str) -> dict:
    if not identity["email_verified"]:
        raise GoogleEmailNotVerifiedError()

    email = normalize_email(identity["email"])
    google_sub = identity["sub"]

    # Mỗi lần thử đều được đếm, kể cả sai mật khẩu; không áp dụng khoảng chờ 60 giây
    check_and_record_request(
        db, PURPOSE, email, dia_chi_ip,
        min_interval_seconds=0,
        email_limit_per_hour=AUTH_LINK_LIMIT_PER_EMAIL_PER_HOUR,
        ip_limit_per_hour=AUTH_LINK_LIMIT_PER_IP_PER_HOUR,
    )

    try:
        if find_user_by_google_sub(db, google_sub) is not None:
            raise GoogleAlreadyLinkedError()

        user = find_user_for_google_link(db, email)  # Khóa dòng tài khoản cùng email
        stored_hash = user["mat_khau_bam"] if user and user["mat_khau_bam"] else _DUMMY_HASH
        password_ok = verify_password(password, stored_hash)
        if user is None or not user["mat_khau_bam"] or not password_ok:
            raise InvalidCredentialsError()
        if user["trang_thai"] != ACTIVE:
            raise AccountLockedError()
        if user["google_sub"] is not None:
            raise AccountAlreadyHasGoogleError()

        if not link_google_sub(db, user["ma_nguoi_dung"], google_sub):
            raise AccountAlreadyHasGoogleError()
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if is_duplicate_key(error, "uq_nd_google_sub"):
            raise GoogleAlreadyLinkedError() from error  # Google này vừa được gắn ở request khác
        raise  # Lỗi ràng buộc khác: báo đúng nguyên nhân
    except Exception:
        db.rollback()
        raise

    # Giữ nguyên vai trò và mật khẩu; chỉ thêm google_sub
    return {
        "ma_nguoi_dung": user["ma_nguoi_dung"],
        "ho_ten": user["ho_ten"],
        "email": user["email"],
        "vai_tro": user["vai_tro"],
    }