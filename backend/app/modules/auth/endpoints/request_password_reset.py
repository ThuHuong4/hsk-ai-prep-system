from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.named_lock import LockNotAcquiredError
from app.database.session import get_db
from app.modules.auth.schemas.request_password_reset_request import RequestPasswordResetRequest
from app.modules.auth.services.enforce_request_limit import RateLimitedError
from app.modules.auth.services.request_password_reset import (
    deliver_password_reset_email,
    request_password_reset,
)
from app.security.client_ip import get_client_ip

router = APIRouter()


@router.post("/auth/request-password-reset", status_code=status.HTTP_202_ACCEPTED)
def post_request_password_reset(
    body: RequestPasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        result = request_password_reset(db, body.email, get_client_ip(request))
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
        background_tasks.add_task(deliver_password_reset_email, **result["gui_email"])
    return {"message": result["message"]}