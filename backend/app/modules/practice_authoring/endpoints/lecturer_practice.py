from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.exam_authoring.schemas.exam_payload import ExamItemsIn
from app.modules.practice_authoring.services import path_service as svc
from app.modules.questions.schemas.question_payload import SKILLS, _clean_text
from app.security.require_lecturer import require_lecturer

router = APIRouter(prefix="/giang-vien")
_LAND_404 = "Không tìm thấy thửa"
_LESSON_404 = "Không tìm thấy bài"


class _Texts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten: str = Field(..., min_length=1, max_length=150)
    muc_tieu: str | None = Field(None, max_length=2000)

    @field_validator("ten", "muc_tieu", mode="before")
    @classmethod
    def _strip(cls, value):
        return _clean_text(value)


class LandIn(_Texts):
    cap_do_id: int = Field(..., ge=1)
    ky_nang: Literal[SKILLS]


class LandUpdateIn(_Texts):
    pass


class LessonIn(_Texts):
    thua_id: int = Field(..., ge=1)
    vi_tri: int = Field(..., ge=1, le=5)  # 1–4 = bài, 5 = kiểm tra cuối thửa
    tai_lieu_id: int | None = Field(None, ge=1)


class LessonUpdateIn(_Texts):
    tai_lieu_id: int | None = Field(None, ge=1)


@router.get("/lo-trinh")
def get_path(cap_do_id: int = Query(..., ge=1), ky_nang: Literal[SKILLS] = Query(...),
             db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    return svc.get_path(db, cap_do_id, ky_nang)


@router.post("/thua", status_code=status.HTTP_201_CREATED)
def post_land(body: LandIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    return {"id": run_service(lambda: svc.create_land(db, body, lecturer["ma_nguoi_dung"])), "message": "Đã tạo thửa nháp"}


@router.put("/thua/{bo_de_id}")
def put_land(body: LandUpdateIn, bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
             lecturer: dict = Depends(require_lecturer)):
    saved = run_service(lambda: svc.update_land(db, bo_de_id, body, lecturer["ma_nguoi_dung"]), _LAND_404)
    return {"id": saved, "message": "Đã lưu thửa" if saved == bo_de_id else "Đã tạo phiên bản nháp mới của thửa"}


@router.post("/thua/{bo_de_id}/vi-tri")
def post_land_move(huong: Literal["len", "xuong"] = Query(...), bo_de_id: int = Path(..., ge=1),
                   db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.move_land(db, bo_de_id, huong), _LAND_404)
    return {"message": "Đã đổi thứ tự thửa"}


@router.post("/thua/{bo_de_id}/{action_name}")
def post_land_status(action_name: Literal["dang", "an", "hien"], bo_de_id: int = Path(..., ge=1),
                     db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.land_status(db, bo_de_id, action_name), _LAND_404)
    return {"message": {"dang": "Đã đăng thửa", "an": "Đã ẩn thửa", "hien": "Đã hiện lại thửa"}[action_name]}


@router.delete("/thua/{bo_de_id}")
def delete_land(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.delete_land(db, bo_de_id), _LAND_404)
    return {"message": "Đã xóa thửa nháp"}


@router.post("/bai-on", status_code=status.HTTP_201_CREATED)
def post_lesson(body: LessonIn, db: Session = Depends(get_db), lecturer: dict = Depends(require_lecturer)):
    return {"id": run_service(lambda: svc.create_lesson(db, body, lecturer["ma_nguoi_dung"]), _LAND_404),
            "message": "Đã tạo bài nháp"}


@router.get("/bai-on/{bo_de_id}")
def get_lesson(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
               _lecturer: dict = Depends(require_lecturer)):
    return run_service(lambda: svc.get_lesson_detail(db, bo_de_id), _LESSON_404)


@router.put("/bai-on/{bo_de_id}")
def put_lesson(body: LessonUpdateIn, bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
               _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.update_lesson(db, bo_de_id, body), _LESSON_404)
    return {"message": "Đã lưu thông tin bài"}


@router.put("/bai-on/{bo_de_id}/cau-hoi")
def put_lesson_items(body: ExamItemsIn, bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                     _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.set_lesson_items(db, bo_de_id, body.cau_hoi), _LESSON_404)
    return {"message": "Đã lưu danh sách câu"}


@router.post("/bai-on/{bo_de_id}/ban-nhap")
def post_lesson_draft(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                      lecturer: dict = Depends(require_lecturer)):
    new_id = run_service(lambda: svc.lesson_draft(db, bo_de_id, lecturer["ma_nguoi_dung"]), _LESSON_404)
    return {"id": new_id, "message": "Đã tạo bản nháp; bản đang dùng vẫn giữ đến khi đăng bản mới"}


@router.post("/bai-on/{bo_de_id}/{action_name}")
def post_lesson_status(action_name: Literal["dang", "an", "hien"], bo_de_id: int = Path(..., ge=1),
                       db: Session = Depends(get_db), _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.lesson_status(db, bo_de_id, action_name), _LESSON_404)
    return {"message": {"dang": "Đã đăng bài", "an": "Đã ẩn bài", "hien": "Đã hiện lại bài"}[action_name]}


@router.delete("/bai-on/{bo_de_id}")
def delete_lesson(bo_de_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                  _lecturer: dict = Depends(require_lecturer)):
    run_service(lambda: svc.delete_lesson(db, bo_de_id), _LESSON_404)
    return {"message": "Đã xóa bài nháp"}
