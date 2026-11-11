import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # D:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường {name} trong .env")
    return value


SMTP_HOST = _require("SMTP_HOST")
SMTP_PORT = int(_require("SMTP_PORT"))
if SMTP_PORT not in (465, 587):
    raise RuntimeError("SMTP_PORT chỉ hỗ trợ 587 (STARTTLS) hoặc 465 (SSL)")

SMTP_USER = _require("SMTP_USER")
SMTP_PASSWORD = _require("SMTP_PASSWORD").replace(" ", "")  # Mật khẩu ứng dụng Gmail không chứa dấu cách
MAIL_FROM_NAME = _require("MAIL_FROM_NAME")

SMTP_TIMEOUT_SECONDS = int(_require("SMTP_TIMEOUT_SECONDS"))
if not 1 <= SMTP_TIMEOUT_SECONDS <= 60:
    raise RuntimeError("SMTP_TIMEOUT_SECONDS phải từ 1 đến 60")