import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # D:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường {name} trong .env")
    return value


def _require_int(name: str, minimum: int, maximum: int) -> int:
    value = int(_require(name))
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} phải từ {minimum} đến {maximum}")
    return value


AUTH_EMAIL_HMAC_KEY = _require("AUTH_EMAIL_HMAC_KEY").encode("utf-8")
if len(AUTH_EMAIL_HMAC_KEY) < 32:
    raise RuntimeError("AUTH_EMAIL_HMAC_KEY phải dài tối thiểu 32 byte")

FRONTEND_URL = _require("FRONTEND_URL").rstrip("/")
if urlparse(FRONTEND_URL).scheme not in ("http", "https") or not urlparse(FRONTEND_URL).netloc:
    raise RuntimeError("FRONTEND_URL phải là URL http/https đầy đủ")

AUTH_TOKEN_TTL_MINUTES = _require_int("AUTH_TOKEN_TTL_MINUTES", 1, 60)
AUTH_RESEND_MIN_SECONDS = _require_int("AUTH_RESEND_MIN_SECONDS", 10, 3600)
AUTH_LIMIT_PER_EMAIL_PER_HOUR = _require_int("AUTH_LIMIT_PER_EMAIL_PER_HOUR", 1, 100)
AUTH_LIMIT_PER_IP_PER_HOUR = _require_int("AUTH_LIMIT_PER_IP_PER_HOUR", 1, 1000)
AUTH_REQUEST_LOG_RETENTION_DAYS = _require_int("AUTH_REQUEST_LOG_RETENTION_DAYS", 1, 365)
AUTH_LINK_LIMIT_PER_EMAIL_PER_HOUR = _require_int("AUTH_LINK_LIMIT_PER_EMAIL_PER_HOUR", 1, 100)
AUTH_LINK_LIMIT_PER_IP_PER_HOUR = _require_int("AUTH_LINK_LIMIT_PER_IP_PER_HOUR", 1, 1000)