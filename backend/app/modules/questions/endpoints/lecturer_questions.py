from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.questions.repositories.list_questions import list_questions
from app.modules.questions.schemas.question_payload import SKILLS, QuestionIn
from app.modules.questions.services.errors import ConflictError, NotFoundError
from app.modules.questions.services.get_question import get_question_detail
from app.modules.questions.services.question_rules import QuestionRuleError
from app.modules.questions.services.question_status import (
    delete_draft_question,
    hide_question,
    publish_question,
    show_question,
)
from app.modules.questions.services.save_question import create_question, update_question_content
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien/cau-hoi")

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy câu hỏi")


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
def get_questions(
    cap_do_id: int | None = Query(None, ge=1),
    ky_nang: Literal[SKILLS] | None = None,
    dang: str | None = Query(None, max_length=20),
    trang_thai: Literal["nhap", "da_dang", "da_an"] | None = None,
    dung_thi_thu: bool = False,
    dung_on_luyen: bool = False,
    q: str | None = Query(None, max_length=100),
    trang: int = Query(1, ge=1),
    so_dong: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _lecturer: dict = Depends(require_lecturer),
):
    filters = {"cap_do_id": cap_do_id, "ky_nang": ky_nang, "dang": dang, "trang_thai": trang_thai,
               "dung_thi_thu": dung_thi_thu, "dung_on_luyen": dung_on_luyen, "q": (q or "").strip() or None}
    return list_questions(db, filters, so_dong, (trang - 1) * so_dong)


@router.get("/{cau_hoi_id}")
def get_question(
    cau_hoi_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _lecturer: dict = Depends(require_lecturer),
):
    item = get_question_detail(db, cau_hoi_id)
    if item is None:
        raise _NOT_FOUND
    return item


@router.post("", status_code=status.HTTP_201_CREATED)
def post_question(body: QuestionIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    new_id = _run(lambda: create_question(db, body, lecturer["ma_nguoi_dung"]))
    return {"id": new_id, "message": "Đã lưu bản nháp"}


@router.put("/{cau_hoi_id}")
def put_question(
    body: QuestionIn,
    cau_hoi_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    lecturer: dict = Depends(require_lecturer),
):
    saved_id = _run(lambda: update_question_content(db, cau_hoi_id, body, lecturer["ma_nguoi_dung"]))
    message = "Đã lưu bản nháp" if saved_id == cau_hoi_id else "Đã tạo phiên bản nháp mới; bản cũ vẫn dùng đến khi đăng bản mới"
    return {"id": saved_id, "message": message}


@router.post("/{cau_hoi_id}/dang")
def post_publish(cau_hoi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                 _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: publish_question(db, cau_hoi_id))
    return {"message": "Đã đăng câu hỏi"}


@router.post("/{cau_hoi_id}/an")
def post_hide(cau_hoi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
              _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: hide_question(db, cau_hoi_id))
    return {"message": "Đã ẩn câu hỏi"}


@router.post("/{cau_hoi_id}/hien")
def post_show(cau_hoi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
              _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: show_question(db, cau_hoi_id))
    return {"message": "Đã hiện lại câu hỏi"}


@router.delete("/{cau_hoi_id}")
def delete_question(cau_hoi_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                    _lecturer: dict = Depends(require_lecturer)):
    _run(lambda: delete_draft_question(db, cau_hoi_id))
    return {"message": "Đã xóa bản nháp"}
