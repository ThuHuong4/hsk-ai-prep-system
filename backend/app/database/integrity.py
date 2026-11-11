from sqlalchemy.exc import IntegrityError

MYSQL_DUPLICATE_ENTRY = 1062


def is_duplicate_key(error: IntegrityError, key_name: str) -> bool:
    """True khi lỗi là MySQL 1062 (trùng giá trị UNIQUE) trên đúng khóa key_name."""
    args = getattr(error.orig, "args", ())
    if len(args) < 2 or args[0] != MYSQL_DUPLICATE_ENTRY:
        return False
    # Thông báo MySQL 8: "Duplicate entry '...' for key 'nguoi_dung.uq_nd_google_sub'"
    return f"'{key_name}'" in str(args[1]) or f".{key_name}'" in str(args[1])