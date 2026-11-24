from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.questions.schemas.question_payload import AssistantIn
from app.modules.questions.services.ai_assistant_service import ask_assistant
from app.modules.questions.services.ai_draft_service import AiDraftError
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/tro-ly-ai")


@router.post("")
def post_assistant(body: AssistantIn, db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    """Giảng viên hỏi trợ lý AI ở bất kỳ trang nào; AI chỉ trả lời và đề xuất, không ghi dữ liệu."""
    try:
        return ask_assistant(db, body)
    except AiDraftError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
