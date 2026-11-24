from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.ai_tutor.services import stateless_tutor
from app.modules.common.schemas import ChatTurnIn as XiangMessage, CheckAnswerIn as CheckIn
from app.modules.common.service_errors import run_service
from app.modules.practice.services import competency_service, lesson_service, level_test_service, path_view, skip_service
from app.security.require_student import require_student

router = APIRouter(prefix="/on-luyen")
_LESSON_404 = "Không tìm thấy bài"
_ATTEMPT_404 = "Không tìm thấy lượt làm bài"


@router.get("/ho-so-ca-nhan")
def personal_dashboard(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return competency_service.get_personal_dashboard(db, student["ma_nguoi_dung"])


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phuong_an_chon_id: int | None = Field(None, ge=1)
    van_ban: str | None = Field(None, max_length=2000)


class SkipAskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    tin_nhan: list[XiangMessage] = Field(..., min_length=1, max_length=20)


class HintIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)


@router.get("/tong-quan")
def overview(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return path_view.overview(db, student["ma_nguoi_dung"])


@router.get("/lo-trinh")
def path(ky_nang: Literal["nghe", "doc", "tu_vung", "viet"] = Query(...), cap_do_id: int | None = Query(None, ge=1),
         db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return path_view.skill_path(db, student["ma_nguoi_dung"], ky_nang, cap_do_id)


@router.post("/bai/{ma_goc_id}/bat-dau")
def start(ma_goc_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return {"luot_id": run_service(lambda: lesson_service.start_lesson(db, ma_goc_id, student["ma_nguoi_dung"]), _LESSON_404)}


@router.get("/luot/{luot_id}")
def get_attempt(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: lesson_service.get_attempt(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


@router.post("/luot/{luot_id}/kiem-tra")
def check(body: CheckIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: lesson_service.check_answer(db, luot_id, student["ma_nguoi_dung"], body), _ATTEMPT_404)


@router.post("/luot/{luot_id}/goi-y")
def open_hint(body: HintIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: lesson_service.open_hint(db, luot_id, student["ma_nguoi_dung"], body.cau_hoi_id), _ATTEMPT_404)


@router.post("/luot/{luot_id}/xem-loi-giai")
def mark_solution_viewed(body: HintIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: lesson_service.mark_solution_viewed(db, luot_id, student["ma_nguoi_dung"], body.cau_hoi_id), _ATTEMPT_404)


@router.post("/luot/{luot_id}/bo", status_code=status.HTTP_204_NO_CONTENT)
def abandon(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: lesson_service.abandon(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


# ---------- Vượt đến thửa (mục 4.2) ----------
_LAND_404 = "Không tìm thấy thửa"


@router.post("/vuot/{thua_ma_goc}/bat-dau")
def start_skip(thua_ma_goc: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return {"luot_id": run_service(lambda: skip_service.start_skip(db, thua_ma_goc, student["ma_nguoi_dung"]), _LAND_404)}


@router.post("/cap/{cap_do_id}/{ky_nang}/{loai}/bat-dau")
def start_level_test(cap_do_id: int = Path(..., ge=1), ky_nang: Literal["nghe", "doc", "tu_vung", "viet"] = Path(...),
                     loai: Literal["bat-dau-cap", "vuot-chang"] = Path(...),
                     db: Session = Depends(get_db), student: dict = Depends(require_student)):
    """Bắt đầu cấp / Vượt chặng (mục 4.2); lượt dùng chung các API /vuot/luot/{id}."""
    kind = loai.replace("-", "_")
    return {"luot_id": run_service(lambda: level_test_service.start(db, student["ma_nguoi_dung"], kind, cap_do_id, ky_nang),
                                   "Không tìm thấy cấp")}


@router.get("/vuot/luot/{luot_id}")
def get_skip(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: skip_service.get_skip(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


@router.put("/vuot/luot/{luot_id}/cau/{cau_hoi_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_skip_answer(body: AnswerIn, luot_id: int = Path(..., ge=1), cau_hoi_id: int = Path(..., ge=1),
                     db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: skip_service.save_answer(db, luot_id, student["ma_nguoi_dung"], cau_hoi_id, body), _ATTEMPT_404)


@router.post("/vuot/luot/{luot_id}/nop")
def submit_skip(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: skip_service.submit_skip(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)
    return run_service(lambda: skip_service.get_skip(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


@router.post("/vuot/luot/{luot_id}/bo", status_code=status.HTTP_204_NO_CONTENT)
def abandon_skip(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: skip_service.abandon_skip(db, luot_id, student["ma_nguoi_dung"]), _ATTEMPT_404)


STUDENT_DAILY_ASK = 60


@router.post("/vuot/luot/{luot_id}/hoi-xiang")
def ask_skip(body: SkipAskIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    uid = student["ma_nguoi_dung"]
    context = run_service(lambda: skip_service.skip_context(db, luot_id, uid, body.cau_hoi_id), _ATTEMPT_404)
    db.close()  # trả kết nối CSDL trước khi chờ AI
    try:
        reply = stateless_tutor.ask(f"hv:{uid}", context, [m.model_dump() for m in body.tin_nhan],
                                    daily=STUDENT_DAILY_ASK, out_msg="Bạn đã dùng hết lượt hỏi Xiang hôm nay, mai hỏi tiếp nhé.")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except stateless_tutor.GuestLimit as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error.message,
                            headers={"Retry-After": str(error.retry_after)})
    except stateless_tutor.GuestAiOff:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Xiang chưa được cấu hình")
    except stateless_tutor.GuestAiError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Xiang đang bận, thử lại sau nhé")
    return {"tra_loi": reply}
