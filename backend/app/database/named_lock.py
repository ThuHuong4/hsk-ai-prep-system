import hashlib
from contextlib import contextmanager

from sqlalchemy import create_engine, text

from app.database.session import DATABASE_URL

# Pool riêng cho khóa: không tranh kết nối với Session, tránh chờ chéo khi tải cao
_lock_engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)

DEFAULT_TIMEOUT_SECONDS = 5


class LockNotAcquiredError(Exception):
    pass


def _lock_name(key: str) -> str:
    # Tên khóa MySQL tối đa 64 ký tự: băm khóa logic thành tên cố định 57 ký tự
    return "hsk_auth_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:48]


@contextmanager
def named_locks(keys: list[str], timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
    """Giữ các khóa GET_LOCK trên MỘT kết nối riêng, độc lập với Session.

    Session có thể commit/rollback và đổi kết nối bên trong khối with;
    khóa vẫn nằm trên kết nối riêng này cho đến khi giải phóng.
    """
    names = sorted({_lock_name(key) for key in keys})  # Cùng thứ tự để tránh khóa chéo
    connection = _lock_engine.connect()
    acquired: list[str] = []
    release_failed = False
    try:
        for name in names:
            result = connection.execute(
                text("SELECT GET_LOCK(:name, :timeout)"),
                {"name": name, "timeout": timeout_seconds},
            ).scalar()
            if result != 1:  # 0 = hết thời gian chờ, NULL = lỗi
                raise LockNotAcquiredError()
            acquired.append(name)
        yield
    finally:
        for name in reversed(acquired):
            try:
                released = connection.execute(
                    text("SELECT RELEASE_LOCK(:name)"), {"name": name}
                ).scalar()
                if released != 1:
                    release_failed = True
            except Exception:
                release_failed = True
        if release_failed:
            # Đóng hẳn kết nối vật lý: MySQL tự giải phóng mọi khóa của kết nối đó
            connection.invalidate()
        connection.close()