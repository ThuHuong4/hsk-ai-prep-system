from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.ai_tutor.services.xiang_chat import AiBusy, AiNotConfigured, AiUnavailable, ask_xiang
from app.modules.common.schemas import ChatTurnIn as ChatMessage
from app.modules.common.service_errors import run_service
from app.security.require_student import require_student

router = APIRouter(prefix="/hoi-xiang")


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    luot_id: int = Field(..., ge=1)
    cau_hoi_id: int = Field(..., ge=1)
    tin_nhan: list[ChatMessage] = Field(..., min_length=1, max_length=20)  # Đoạn chat hiện tại, tin cuối là câu hỏi mới


@router.post("")
def ask(body: AskIn, db: Session = Depends(get_db), student: dict = Depends(require_student)):
    def action():
        try:
            reply = ask_xiang(db, student["ma_nguoi_dung"], body.luot_id, body.cau_hoi_id,
                              [m.model_dump() for m in body.tin_nhan])
        except AiNotConfigured:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Hỏi Xiang chưa được cấu hình trên máy chủ")
        except AiBusy as error:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, error.message)
        except AiUnavailable:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Xiang tạm thời chưa trả lời được, bạn thử lại sau nhé")
        return {"tra_loi": reply}

    return run_service(action, "Không tìm thấy câu hỏi trong bài làm của bạn")