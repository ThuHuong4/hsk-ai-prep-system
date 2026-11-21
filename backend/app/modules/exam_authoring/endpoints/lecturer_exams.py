from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.exam_authoring.repositories.exam_rows import list_exams
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemsIn
from app.modules.exam_authoring.services import exam_service as svc
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
