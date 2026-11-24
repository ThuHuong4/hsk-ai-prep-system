"""Giảng viên soạn đề thi thử mới với AI theo từng phần (cấu trúc HSK 2.0), kèm tạo hình và giọng đọc."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exam_authoring.schemas.exam_payload import (
    AiAudioIn,
    AiImageIn,
    AiPartApproveIn,
    AiPartChatIn,
    AiPartIn,
)
from app.modules.exam_authoring.services import ai_part_service as svc
from app.modules.exam_authoring.services.ai_media_service import AiMediaError, make_audio, make_image
from app.modules.exam_authoring.services.hsk_blueprint import BLUEPRINT
from app.modules.questions.services.ai_draft_service import AiDraftError
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/de-thi")


def _run(action):
    try:
        return action()
    except (AiDraftError, AiMediaError) as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)


@router.get("/ai-cau-truc")
def get_blueprint(cap_do_id: int = Query(..., ge=1), db: Session = Depends(get_db),
                  _lecturer: dict = Depends(require_lecturer)):
    """Cấu trúc đề HSK 2.0 của cấp: các phần, số câu, thời lượng; kèm tình trạng cấu hình AI."""
    return _run(lambda: svc.blueprint_for(db, cap_do_id))


@router.post("/ai-phan/soan")
def post_generate_part(body: AiPartIn, db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    """AI soạn nội dung một phần; chưa ghi CSDL."""
    return _run(lambda: svc.generate_part(db, body))


@router.post("/ai-phan/trao-doi")
def post_chat_part(body: AiPartChatIn, db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    """Giảng viên trao đổi với AI về một phần; AI chỉ đề xuất bản sửa."""
    return _run(lambda: svc.chat_part(db, body))


@router.post("/ai-phan/duyet")
def post_approve_part(body: AiPartApproveIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    """Giảng viên duyệt phần: lưu và đăng từng câu (ghi người duyệt), trả id câu để ghép đề."""
    return _run(lambda: svc.approve_part(db, body, lecturer["ma_nguoi_dung"]))


@router.post("/ai-tep/hinh")
def post_image(body: AiImageIn, _lecturer: dict = Depends(require_lecturer)):
    return {"duong_dan": _run(lambda: make_image(body.mo_ta))}


@router.post("/ai-tep/am-thanh")
def post_audio(body: AiAudioIn, db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    """Đọc lời nghe nhiều giọng; HSK 1–3 phát 2 lần trong cùng tệp, HSK 1–2 đọc chậm hơn."""
    def action():
        _, level = svc.resolve_level(db, body.cap_do_id)
        db.rollback()
        return make_audio(body.loi_nghe, plays=BLUEPRINT[level]["phat_nghe"], slow=level <= 2)
    return {"duong_dan": _run(action)}
