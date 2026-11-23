"""Cấu hình môi trường cho nhà cung cấp AI (OpenAI hoặc cổng tương thích OpenAI như Gemini/OpenRouter)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]  # d:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")

# Không bắt buộc khi khởi động: thiếu khóa thì chỉ tính năng AI báo chưa cấu hình, các phần khác vẫn hoạt động bình thường
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
OPENAI_TIMEOUT_SECONDS = 30


def ai_ready() -> bool:
    """Kiểm tra hệ thống đã khai báo đủ khóa API và tên mô hình AI chưa."""
    return bool(OPENAI_API_KEY and OPENAI_MODEL)
