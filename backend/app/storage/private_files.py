"""Tệp cần kiểm tra quyền trước khi trả (tài liệu ôn tập): lưu ngoài thư mục /media công khai."""
import shutil
import uuid
from pathlib import Path

PRIVATE_DIR = Path(__file__).resolve().parents[2] / "private_uploads"  # D:\HSK_AI\backend\private_uploads
DOCUMENTS = "documents"


def resolve(relative: str) -> Path:
    """Đường dẫn tuyệt đối an toàn (không thoát khỏi PRIVATE_DIR)."""
    target = (PRIVATE_DIR / relative).resolve()
    if PRIVATE_DIR.resolve() not in target.parents:
        raise ValueError("Đường dẫn tệp không hợp lệ")
    return target


def save_document(data: bytes, ext: str) -> str:
    folder = PRIVATE_DIR / DOCUMENTS
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return f"{DOCUMENTS}/{name}"


def copy_document(relative: str) -> str:
    """Sao tệp sang tên mới (phiên bản mới cần đường dẫn riêng)."""
    source = resolve(relative)
    ext = source.suffix.lstrip(".")
    new_relative = f"{DOCUMENTS}/{uuid.uuid4().hex}.{ext}"
    shutil.copyfile(source, resolve(new_relative))
    return new_relative


def delete_file(relative: str) -> None:
    try:
        resolve(relative).unlink(missing_ok=True)
    except (OSError, ValueError):
        pass
