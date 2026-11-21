from sqlalchemy import text
from sqlalchemy.orm import Session

# Bảng có dòng gốc tự trỏ (ma_goc_id = id): cấp trước id để chèn dòng gốc trong một lệnh.
_TABLES = {"cau_hoi", "bo_de", "tai_lieu"}


def next_root_id(db: Session, table: str) -> int:
    """Gọi trong giao dịch; FOR UPDATE khóa cuối chỉ mục khóa chính để hai yêu cầu không lấy trùng id."""
    if table not in _TABLES:
        raise ValueError("Bảng không hỗ trợ cấp id gốc")
    current = db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table} FOR UPDATE")).scalar_one()
    return int(current) + 1
