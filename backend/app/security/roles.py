from enum import IntEnum


class Role(IntEnum):
    """Khớp bảng vai_tro trong CSDL."""

    HOC_VIEN = 1
    QUAN_TRI_VIEN = 2
    GIANG_VIEN = 3


# Vai trò duy nhất được gán khi người dùng tự tạo tài khoản (email/mật khẩu hoặc Google)
SELF_SIGNUP_ROLE = Role.HOC_VIEN