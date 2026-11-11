import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # D:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường {name} trong .env")
    return value


JWT_SECRET_KEY = _require("JWT_SECRET_KEY")
if len(JWT_SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET_KEY phải dài tối thiểu 32 byte")

JWT_ALGORITHM = _require("JWT_ALGORITHM")
if JWT_ALGORITHM != "HS256":
    raise RuntimeError("JWT_ALGORITHM chỉ hỗ trợ HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(_require("ACCESS_TOKEN_EXPIRE_MINUTES"))
if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES phải lớn hơn 0")