import hashlib
import re
import secrets

TOKEN_BYTES = 32
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")  # 32 byte -> 43 ký tự base64url


def generate_token() -> tuple[str, bytes]:
    """Trả (token gốc để gửi trong liên kết, bản băm 32 byte để lưu CSDL)."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hash_token(token)


def is_well_formed(token: str) -> bool:
    return isinstance(token, str) and bool(_TOKEN_PATTERN.fullmatch(token))


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()