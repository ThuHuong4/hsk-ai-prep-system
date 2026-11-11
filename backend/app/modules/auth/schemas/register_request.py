import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.password_policy import validate_password_strength

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ho_ten: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str

    @field_validator("ho_ten")
    @classmethod
    def check_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Họ tên không được để trống")
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("Họ tên chứa ký tự không hợp lệ")
        return value

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        if not _EMAIL_PATTERN.fullmatch(value.strip()):
            raise ValueError("Email không hợp lệ")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)