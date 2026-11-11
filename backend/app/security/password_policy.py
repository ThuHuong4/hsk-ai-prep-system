MIN_LENGTH = 8
MAX_LENGTH = 128


def validate_password_strength(value: str) -> str:
    if not MIN_LENGTH <= len(value) <= MAX_LENGTH:
        raise ValueError(f"Mật khẩu phải từ {MIN_LENGTH} đến {MAX_LENGTH} ký tự")
    if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái và 1 chữ số")
    return value