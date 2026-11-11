from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.named_lock import LockNotAcquiredError
from app.database.session import get_db
from app.modules.auth.services.enforce_request_limit import RateLimitedError
from app.modules.auth.services.register_user import deliver_verification_email
from app.modules.auth.services.resend_verification import resend_verification
from app.security.client_ip import get_client_ip

router = APIRouter()


class ResendVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=255)


@router.post("/auth/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def post_resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        result = resend_verification(db, body.email, get_client_ip(request))
    except RateLimitedError as error:
        seconds = error.retry_after_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Vui lòng chờ {seconds} giây rồi thử lại" if seconds else "Bạn đã gửi quá nhiều yêu cầu, vui lòng thử lại sau",
            headers={"Retry-After": str(seconds)} if seconds else None,
        )
    except LockNotAcquiredError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Hệ thống đang bận, vui lòng thử lại")

    if result["gui_email"]:
        background_tasks.add_task(deliver_verification_email, **result["gui_email"])
    return {"message": result["message"]}