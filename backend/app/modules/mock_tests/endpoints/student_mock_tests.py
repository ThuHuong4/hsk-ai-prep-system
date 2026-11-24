"""Các điểm cuối HTTP (FastAPI Endpoints) cho phân hệ Thi thử HSK của Học viên (`AT17`–`AT22`, `AT41`–`AT43`).

- Vai trò: Chỉ cho phép Học viên đã đăng nhập vào phòng chờ chọn cấp HSK (mặc định theo cấp Đánh giá đầu vào)
  và nhận đề thi ngẫu nhiên; từ chối hoàn toàn việc xem danh sách đề hoặc chỉ định mã đề cố định (`AT42`).
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.common.service_errors import run_service
from app.modules.mock_tests.services import attempt_service as svc
from app.security.require_student import require_student

router = APIRouter(prefix="/thi-thu")
_LEVEL_404 = "Không tìm thấy cấp độ HSK"
_ATTEMPT_404 = "Không tìm thấy lượt làm bài"
_FORBIDDEN_CATALOG = "Đề thi được bảo mật trước giờ thi; hệ thống cấp đề ngẫu nhiên theo cấp độ HSK sau khi đăng nhập."


class StartExamIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Giữ tương thích ngược nếu test tự động gửi kèm, nhưng dịch vụ luôn khóa theo trình độ hiện tại của học viên
    cap_do_id: int | None = Field(None, ge=1)


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    phuong_an_chon_id: int | None = Field(None, ge=1)
    van_ban: str | None = Field(None, max_length=2000)
    vi_tri: int | None = Field(None, ge=1, le=500)


class SubmitExamIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    het_gio: bool = False
    thu_bai_vi_pham: bool = False


# Chặn tường minh các đường dẫn danh mục đề & bắt đầu theo ID đề cũ (AT42)
@router.get("/de", include_in_schema=False)
def blocked_list_exams():
    raise HTTPException(status_code=403, detail=_FORBIDDEN_CATALOG)


@router.get("/de/{ma_goc_id}", include_in_schema=False)
def blocked_exam_info(ma_goc_id: int = Path(..., ge=1)):
    raise HTTPException(status_code=403, detail=_FORBIDDEN_CATALOG)


@router.post("/de/{ma_goc_id}/bat-dau", include_in_schema=False)
def blocked_start_by_exam_id(ma_goc_id: int = Path(..., ge=1)):
    raise HTTPException(status_code=403, detail=_FORBIDDEN_CATALOG)


# Học viên: xem phòng chờ Thi thử bảo mật (không chọn cấp) & bắt đầu đề ngẫu nhiên theo trình độ hiện tại
@router.get("/chon-cap")
def get_lobby(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return svc.get_exam_lobby(db, student["ma_nguoi_dung"])


@router.post("/bat-dau")
def start_random(
    _body: StartExamIn | None = Body(default=None),
    db: Session = Depends(get_db),
    student: dict = Depends(require_student),
):
    return run_service(lambda: svc.start_random_exam(db, student["ma_nguoi_dung"]), _LEVEL_404)


@router.get("/lich-su")
def history(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return svc.history(db, student["ma_nguoi_dung"])


@router.get("/luot/{luot_id}")
def get_attempt(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: svc.get_attempt(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


@router.put("/luot/{luot_id}/tra-loi")
def save_answer(
    body: AnswerIn,
    luot_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    student: dict = Depends(require_student),
):
    return run_service(lambda: svc.save_answer(db, luot_id, student["ma_nguoi_dung"], body), _ATTEMPT_404)


@router.post("/luot/{luot_id}/chuyen-phan")
def advance_section(
    luot_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    student: dict = Depends(require_student),
):
    return run_service(lambda: svc.advance_section(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


@router.post("/luot/{luot_id}/nop")
def submit(
    body: SubmitExamIn | None = Body(default=None),
    luot_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    student: dict = Depends(require_student),
):
    res = run_service(
        lambda: svc.submit_attempt(
            db,
            luot_id,
            student["ma_nguoi_dung"],
            het_gio=bool(body and body.het_gio),
            thu_bai_vi_pham=bool(body and body.thu_bai_vi_pham),
        ),
        _ATTEMPT_404,
    )
    return {"message": "Đã nộp bài", **res}


@router.get("/luot/{luot_id}/ket-qua")
def result(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: svc.get_result(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)
