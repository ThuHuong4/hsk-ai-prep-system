"""Lỗi nghiệp vụ dùng chung và cách đổi sang mã HTTP cho các mô-đun Giảng viên."""
from fastapi import HTTPException, status

from app.modules.questions.services.errors import ConflictError, NotFoundError
from app.modules.questions.services.question_rules import QuestionRuleError as RuleError

__all__ = ["ConflictError", "NotFoundError", "RuleError", "run_service"]


def run_service(action, not_found: str = "Không tìm thấy dữ liệu"):
    try:
        return action()
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)
    except RuleError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.message)
    except ConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.message)
