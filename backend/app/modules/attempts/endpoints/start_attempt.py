from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.attempts.services.start_attempt import (
    AttemptExpiredError,
    ExamNotAvailableError,
    UserNotFoundError,
    start_exam_attempt,
)
from app.security.current_user import get_current_user

router = APIRouter()


class StartAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_bo_de: int = Field(..., ge=1)


@router.post("/attempts")
def start_attempt(
    body: StartAttemptRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = start_exam_attempt(db, current_user["ma_nguoi_dung"], body.ma_bo_de)
    except ExamNotAvailableError:
        raise HTTPException(status_code=404, detail="Đề thi không tồn tại hoặc chưa xuất bản")
    except AttemptExpiredError:
        # Tạm thời: bước nộp bài sẽ tự chấm lượt quá hạn
        raise HTTPException(status_code=409, detail="Lượt thi đã hết giờ")
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập hoặc token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    response.status_code = status.HTTP_200_OK if result["khoi_phuc"] else status.HTTP_201_CREATED
    return result