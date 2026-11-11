from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"  # D:\HSK_AI\backend\uploads


def register_static_media(app: FastAPI) -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=UPLOADS_DIR), name="media")