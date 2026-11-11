from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.named_lock import LockNotAcquiredError
from app.database.session import get_db
from app.modules.auth.schemas.register_request import RegisterRequest
from app.modules.auth.services.enforce_request_limit import RateLimitedError
from app.modules.auth.services.register_user import deliver_verification_email, register_user
from app.security.client_ip import get_client_ip

router = APIRouter()


@router.post("/auth/register", status_code=status.HTTP_202_ACCEPTED)
def register(
    body: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        result = register_user(db, body.ho_ten, body.email, body.password, get_client_ip(request))
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