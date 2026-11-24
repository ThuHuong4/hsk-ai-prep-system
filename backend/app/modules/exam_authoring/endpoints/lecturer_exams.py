from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exam_authoring.repositories.exam_rows import list_exams
from app.modules.exam_authoring.schemas.exam_payload import AiComposeIn, AiCreateExamIn, ExamInfoIn, ExamItemsIn
from app.modules.exam_authoring.services.ai_exam_service import AiExamError, compose_exam, create_exam_from_ai
from app.modules.exam_authoring.services.ai_media_service import AiMediaError
from app.modules.exam_authoring.services import exam_service as svc
from app.modules.exam_authoring.services import listening_audio
from app.modules.questions.services.errors import ConflictError, NotFoundError
from app.modules.questions.services.question_rules import QuestionRuleError
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/de-thi")

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đề thi")


def _run(action):
    try:
        return action()
    except NotFoundError:
        raise _NOT_FOUND
    except QuestionRuleError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.message)
    except ConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.message)


@router.get("")
def get_exams(
    cap_do_id: int | None = Query(None, ge=1),
    trang_thai: Literal["nhap", "da_dang", "da_an"] | None = None,
    q: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
    _lecturer: dict = Depends(require_lecturer),
):
    return list_exams(db, cap_do_id, trang_thai, (q or "").strip() or None)


@router.get("/{bo_de_id}")
def get_exam(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
             _lecturer: dict = Depends(require_lecturer)):
    exam = svc.get_exam_detail(db, bo_de_id)
    if exam is None:
        raise _NOT_FOUND
    return exam


@router.post("/ai-ghep")
def post_ai_compose(body: AiComposeIn, db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    """AI chọn câu đã duyệt cho đề theo cấu trúc phần; chưa ghi CSDL."""
    try:
        return compose_exam(db, body)
    except AiExamError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)


@router.post("/ai-tao", status_code=status.HTTP_201_CREATED)
def post_ai_create(body: AiCreateExamIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    """Tạo đề nháp từ danh sách câu Giảng viên đã xem; đăng đề ở trang soạn đề."""
    new_id = _run(lambda: create_exam_from_ai(db, body, lecturer["ma_nguoi_dung"]))
    return {"id": new_id, "message": "Đã tạo đề nháp. Kiểm tra rồi bấm Đăng."}


@router.post("", status_code=status.HTTP_201_CREATED)
def post_exam(body: ExamInfoIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    new_id = _run(lambda: svc.create_exam(db, body, lecturer["ma_nguoi_dung"]))
    return {"id": new_id, "message": "Đã tạo đề nháp"}


@router.put("/{bo_de_id}")
def put_exam(body: ExamInfoIn, bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
             _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.update_exam_info(db, bo_de_id, body))
    return {"id": bo_de_id, "message": "Đã lưu thông tin đề"}


@router.put("/{bo_de_id}/cau-hoi")
def put_exam_items(body: ExamItemsIn, bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                   _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.set_exam_items(db, bo_de_id, body.cau_hoi))
    return {"message": "Đã lưu danh sách câu"}


@router.post("/{bo_de_id}/ban-nhap")
def post_draft(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
               lecturer: dict = Depends(require_lecturer)):
    new_id = _run(lambda: svc.create_draft_version(db, bo_de_id, lecturer["ma_nguoi_dung"]))
    return {"id": new_id, "message": "Đã tạo bản nháp; bản đang dùng vẫn giữ đến khi đăng bản mới"}


@router.post("/{bo_de_id}/ghep-bang-nghe")
def post_build_listening_tape(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                              _lecturer: dict = Depends(require_lecturer)):
    """Tự động ghép toàn bộ câu Nghe của đề thành 1 băng MP3 liên tiếp chuẩn phòng thi HSK."""
    exam = svc.get_exam_detail(db, bo_de_id)
    if exam is None:
        raise _NOT_FOUND
    if exam["trang_thai"] != "nhap":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Chỉ ghép lại băng Nghe cho đề ở trạng thái nháp")
    try:
        res = listening_audio.build_for_exam_db(db, bo_de_id)
    except AiMediaError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message)
    if not res:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Đề chưa có câu Nghe nào để ghép băng")
    return {**res, "message": f"Đã ghép băng Nghe liên tiếp ({res['so_cau_nghe']} câu · {res['giay']} giây)"}


@router.post("/{bo_de_id}/dang")
def post_publish(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.publish_exam(db, bo_de_id))
    return {"message": "Đã đăng đề"}


@router.post("/{bo_de_id}/an")
def post_hide(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
              _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.hide_exam(db, bo_de_id))
    return {"message": "Đã ẩn đề"}


@router.post("/{bo_de_id}/hien")
def post_show(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
              _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.show_exam(db, bo_de_id))
    return {"message": "Đã hiện lại đề"}


@router.delete("/{bo_de_id}")
def delete_exam(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: svc.delete_draft_exam(db, bo_de_id))
    return {"message": "Đã xóa đề nháp"}
