import hashlib
import hmac

from app.core.auth_config import AUTH_EMAIL_HMAC_KEY


def normalize_email(email: str) -> str:
    # Chỉ cắt khoảng trắng và chuyển chữ thường; không bỏ dấu chấm hay phần +...
    return email.strip().lower()


def email_hmac(email: str) -> bytes:
    normalized = normalize_email(email)
    return hmac.new(AUTH_EMAIL_HMAC_KEY, normalized.encode("utf-8"), hashlib.sha256).digest()