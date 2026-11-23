"""API công khai cho Khách học thử Ôn luyện. Không cần đăng nhập, không ghi CSDL."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.ai_tutor.services import stateless_tutor
from app.modules.common.schemas import ChatTurnIn as GuestMessage, CheckAnswerIn as CheckIn
from app.modules.common.service_errors import run_service
from app.modules.practice.services import guest_service
from app.security.client_ip import get_client_ip

router = APIRouter(prefix="/cong-khai")
_LESSON_404 = "Không tìm thấy bài"


class GuestAskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bai_ma_goc_id: int = Field(..., ge=1)
    cau_hoi_id: int = Field(..., ge=1)
    phuong_an_chon_id: int | None = Field(None, ge=1)
    van_ban: str | None = Field(None, max_length=2000)
    tin_nhan: list[GuestMessage] = Field(..., min_length=1, max_length=20)


@router.get("/on-luyen/tong-quan")
def guest_overview(db: Session = Depends(get_db)):
    return guest_service.guest_overview(db)


@router.get("/on-luyen/lo-trinh")
def guest_path(ky_nang: Literal["nghe", "doc", "tu_vung", "viet"] = Query(...), cap_do_id: int | None = Query(None, ge=1),
               db: Session = Depends(get_db)):
    return guest_service.guest_path(db, ky_nang, cap_do_id)


@router.get("/on-luyen/bai/{ma_goc_id}")
def guest_lesson(ma_goc_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return run_service(lambda: guest_service.guest_lesson(db, ma_goc_id), _LESSON_404)


@router.post("/on-luyen/bai/{ma_goc_id}/kiem-tra")
def guest_check(body: CheckIn, ma_goc_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return run_service(lambda: guest_service.guest_check(db, ma_goc_id, body), _LESSON_404)


@router.post("/hoi-xiang")
def guest_ask(body: GuestAskIn, request: Request, db: Session = Depends(get_db)):
    context = run_service(
        lambda: guest_service.guest_context(db, body.bai_ma_goc_id, body.cau_hoi_id, body.phuong_an_chon_id, body.van_ban),
        _LESSON_404,
    )
    db.close()  # trả kết nối CSDL trước khi chờ AI
    ip = get_client_ip(request)
    try:
        reply = stateless_tutor.ask(ip, context, [m.model_dump() for m in body.tin_nhan])
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except stateless_tutor.GuestLimit as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error.message,
                            headers={"Retry-After": str(error.retry_after)})
    except stateless_tutor.GuestAiOff:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Xiang chưa được cấu hình")
    except stateless_tutor.GuestAiError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Xiang đang bận, thử lại sau nhé")
    return {"tra_loi": reply, "con_lai": stateless_tutor.remaining(ip)}
