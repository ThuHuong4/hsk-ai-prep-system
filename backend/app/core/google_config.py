import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # D:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
if not GOOGLE_CLIENT_ID.endswith(".apps.googleusercontent.com"):
    raise RuntimeError("GOOGLE_CLIENT_ID trong .env không hợp lệ")