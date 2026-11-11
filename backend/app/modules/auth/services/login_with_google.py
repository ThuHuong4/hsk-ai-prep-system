from app.database.integrity import is_duplicate_key
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.repositories.create_user import create_google_student
from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.modules.auth.repositories.find_user_by_google_sub import find_user_by_google_sub
from app.modules.auth.services.authenticate_user import AccountLockedError
from app.security.email_identity import normalize_email

ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa


class GoogleEmailNotVerifiedError(Exception):
    pass


class AccountLinkRequiredError(Exception):
    pass


def _display_name(identity: dict, email: str) -> str:
    name = "".join(ch for ch in identity["name"] if ord(ch) >= 32).strip()
    return (name or email.split("@", 1)[0])[:100]


def login_with_google(db: Session, identity: dict) -> dict:
    if not identity["email_verified"]:
        raise GoogleEmailNotVerifiedError()

    email = normalize_email(identity["email"])
    google_sub = identity["sub"]
    try:
        user = find_user_by_google_sub(db, google_sub)
        if user is None:
            if find_user_by_email(db, email) is not None:
                # Email đã thuộc tài khoản khác: không tự liên kết khi chưa xác thực
                raise AccountLinkRequiredError()
            try:
                create_google_student(db, _display_name(identity, email), email, google_sub)
                db.commit()
            except IntegrityError as error:
                db.rollback()
                # Chỉ bỏ qua khi request đồng thời đã tạo trước (trùng google_sub hoặc email)
                if not (is_duplicate_key(error, "uq_nd_google_sub") or is_duplicate_key(error, "email")):
                    raise
            user = find_user_by_google_sub(db, google_sub)
            if user is None:
                raise AccountLinkRequiredError()  # Email vừa bị một tài khoản mật khẩu chiếm

        if user["trang_thai"] != ACTIVE:
            raise AccountLockedError()
        db.rollback()  # Kết thúc transaction chỉ đọc
    except Exception:
        db.rollback()
        raise

    return {
        "ma_nguoi_dung": user["ma_nguoi_dung"],
        "ho_ten": user["ho_ten"],
        "email": user["email"],
        "vai_tro": user["vai_tro"],
    }