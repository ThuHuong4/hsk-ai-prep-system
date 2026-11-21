from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_RESEND_MIN_SECONDS
from app.database.named_lock import LockNotAcquiredError
from app.database.session import get_db
from app.modules.auth.services.enforce_request_limit import RateLimitedError
from app.modules.auth.services.register_user import deliver_verification_email
from app.modules.auth.services.resend_verification import AlreadyVerifiedError, resend_verification
from app.security.client_ip import get_client_ip
from app.security.current_user import get_current_user

router = APIRouter()


@router.post("/auth/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def post_resend_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        mail = resend_verification(db, current_user, get_client_ip(request))
    except AlreadyVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"ma_loi": "DA_XAC_MINH", "thong_bao": "Email của bạn đã được xác minh."},
        )
    except RateLimitedError as error:
        seconds = error.retry_after_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Vui lòng chờ {seconds} giây rồi thử lại" if seconds else "Bạn đã gửi quá nhiều yêu cầu, vui lòng thử lại sau",
            headers={"Retry-After": str(seconds)} if seconds else None,
        )
    except LockNotAcquiredError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Hệ thống đang bận, vui lòng thử lại")

    background_tasks.add_task(deliver_verification_email, **mail)
    return {
        "message": (
            f"Đã gửi thư xác minh tới {mail['email']}. Hãy kiểm tra cả thư mục Spam; "
            f"có thể gửi lại sau {AUTH_RESEND_MIN_SECONDS} giây."
        )
    }
