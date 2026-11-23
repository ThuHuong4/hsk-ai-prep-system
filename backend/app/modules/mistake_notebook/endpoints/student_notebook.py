from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.ai_tutor.services import stateless_tutor
from app.modules.common.schemas import ChatTurnIn as XiangMessage, CheckAnswerIn as CheckIn
from app.modules.common.service_errors import run_service
from app.modules.mistake_notebook.services import missions, notebook_service as svc
from app.security.require_student import require_student

router = APIRouter()
_LUOT_404 = "Không tìm thấy lượt ôn"


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cau_hoi_id: int = Field(..., ge=1)
    tin_nhan: list[XiangMessage] = Field(..., min_length=1, max_length=20)


@router.get("/so-tay")
def get_notebook(trang_thai: Literal["can_on", "cho_on_lai", "da_cung_co"] | None = Query(None),
                 db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return svc.list_notebook(db, student["ma_nguoi_dung"], trang_thai)


@router.post("/so-tay/on")
def start_review(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return {"luot_id": run_service(lambda: svc.start_review(db, student["ma_nguoi_dung"]))}


@router.get("/so-tay/luot/{luot_id}")
def get_review(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: svc.get_review(db, luot_id, student["ma_nguoi_dung"]), _LUOT_404)


@router.post("/so-tay/luot/{luot_id}/kiem-tra")
def check(body: CheckIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return run_service(lambda: svc.check_answer(db, luot_id, student["ma_nguoi_dung"], body), _LUOT_404)


@router.post("/so-tay/luot/{luot_id}/bo", status_code=status.HTTP_204_NO_CONTENT)
def abandon(luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    run_service(lambda: svc.abandon(db, luot_id, student["ma_nguoi_dung"]), _LUOT_404)


@router.post("/so-tay/luot/{luot_id}/hoi-xiang")
def ask(body: AskIn, luot_id: int = Path(..., ge=1), db: Session = Depends(get_db), student: dict = Depends(require_student)):
    uid = student["ma_nguoi_dung"]
    context = run_service(lambda: svc.review_context(db, luot_id, uid, body.cau_hoi_id), _LUOT_404)
    db.close()
    try:
        reply = stateless_tutor.ask(f"hv:{uid}", context, [m.model_dump() for m in body.tin_nhan],
                                    daily=60, out_msg="Bạn đã dùng hết lượt hỏi Xiang hôm nay, mai hỏi tiếp nhé.")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except stateless_tutor.GuestLimit as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error.message, headers={"Retry-After": str(error.retry_after)})
    except (stateless_tutor.GuestAiOff, stateless_tutor.GuestAiError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Xiang đang bận, thử lại sau nhé")
    return {"tra_loi": reply}


# ---------- Nhiệm vụ ngày (mục 4.5) ----------
@router.get("/nhiem-vu")
def get_missions(db: Session = Depends(get_db), student: dict = Depends(require_student)):
    return missions.list_missions(db, student["ma_nguoi_dung"])


@router.post("/nhiem-vu/{ma}/nhan")
def claim_mission(ma: Literal["nv_so_tay", "nv_on_luyen", "nv_thi_thu"] = Path(...), db: Session = Depends(get_db),
                  student: dict = Depends(require_student)):
    return run_service(lambda: missions.claim(db, student["ma_nguoi_dung"], ma), "Không tìm thấy nhiệm vụ")
