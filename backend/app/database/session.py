"""Quản lý kết nối phiên CSDL MySQL (SQLAlchemy Engine & Session).

- Vai trò: Cấp phát kết nối CSDL cho mọi API qua dependency `get_db()`.
- Luồng xử lý: Đọc biến môi trường `.env` -> Tạo `engine` (pool_pre_ping) -> Tự động ép `time_zone = '+07:00'`
  cho mọi kết nối MySQL mới để `NOW()` và `CURDATE()` luôn tính đúng ngày giờ Việt Nam (phục vụ chuỗi ngày học, hạn đề thi).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parents[2]  # D:\HSK_AI\backend
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD") or None,
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME"),
    query={"charset": "utf8mb4"},
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _set_vietnam_timezone(dbapi_connection, _connection_record) -> None:
    """Cố định múi giờ phiên MySQL về giờ Việt Nam (+07:00) ngay khi mở kết nối."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET time_zone = '+07:00'")
    finally:
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT @@session.time_zone, NOW()")).one()
        print("Kết nối MySQL OK, múi giờ phiên =", result[0], "| NOW() =", result[1])
