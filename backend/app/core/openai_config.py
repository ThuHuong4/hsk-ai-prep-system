import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # D:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")

# Không bắt buộc khi khởi động: thiếu key thì chỉ riêng Hỏi Xiang báo chưa cấu hình, phần khác vẫn chạy
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None  # Trống = máy chủ OpenAI; có giá trị = nhà cung cấp tương thích (Gemini…)
OPENAI_TIMEOUT_SECONDS = 30


def openai_ready() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_MODEL)