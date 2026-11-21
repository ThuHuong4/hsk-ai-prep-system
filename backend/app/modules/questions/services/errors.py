class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    """Thao tác không hợp lệ với trạng thái hiện tại (trả 409 kèm thông báo)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
