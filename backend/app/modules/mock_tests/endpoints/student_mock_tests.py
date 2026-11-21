from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.mock_tests.services import attempt_service as svc
from app.security.require_student import require_student

router = APIRouter(prefix="/thi-thu")
_EXAM_404 = "Không tìm thấy đề thi"
_ATTEMPT_404 = "Không tìm thấy lượt làm bài"


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    phuong_an_chon_id: int | None = Field(None, ge=1)
    van_ban: str | None = Field(None, max_length=2000)
    vi_tri: int | None = Field(None, ge=1, le=500)


# Công khai: khách xem được danh sách và thông tin đề
@router.get("/de")
def list_exams(cap_do_id: int = Query(..., ge=1), db: Session = Depends(get_db)):
    return svc.list_exams(db, cap_do_id)


@router.get("/de/{ma_goc_id}")
def exam_info(ma_goc_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return run_service(lambda: svc.exam_info(db, ma_goc_id), _EXAM_404)


# Học viên
@router.post("/de/{ma_goc_id}/bat-dau")
def start(ma_goc_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return {"luot_id": run_service(lambda: svc.start_attempt(db, ma_goc_id, student["ma_nguoi_dung"]), _EXAM_404)}


@router.get("/lich-su")
def history(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return svc.history(db, student["ma_nguoi_dung"])


@router.get("/luot/{luot_id}")
def get_attempt(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: svc.get_attempt(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


@router.put("/luot/{luot_id}/tra-loi")
def save_answer(body: AnswerIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db),
                student: dict = Depends(require_student)):
    return run_service(lambda: svc.save_answer(db, luot_id, student["ma_nguoi_dung"], body), _ATTEMPT_404)


@router.post("/luot/{luot_id}/nop")
def submit(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: svc.submit_attempt(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)
    return {"message": "Đã nộp bài"}


@router.get("/luot/{luot_id}/ket-qua")
def result(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: svc.get_result(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)
