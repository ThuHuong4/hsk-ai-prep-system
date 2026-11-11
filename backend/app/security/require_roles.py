from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.security.current_user import get_current_user
from app.security.roles import Role


def require_roles(*allowed: Role) -> Callable[..., dict]:
    """Tạo dependency chỉ cho phép các vai trò trong danh sách."""
    allowed_values = {int(role) for role in allowed}

    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["vai_tro"] not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập",
            )
        return current_user

    return dependency