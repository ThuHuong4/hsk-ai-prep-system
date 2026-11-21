from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES
from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.modules.auth.repositories.save_account_token import issue_account_token
from app.modules.auth.services.enforce_request_limit import check_and_record_request
from app.security.one_time_token import generate_token


class AlreadyVerifiedError(Exception):
    pass


def resend_verification(db: Session, current_user: dict, dia_chi_ip: str) -> dict:
    """Người đã đăng nhập tự yêu cầu thư xác minh cho email của mình.
    Trả dữ liệu nội bộ để gửi nền, không trả cho client."""
    email = current_user["email"]
    check_and_record_request(db, "xac_minh_email", email, dia_chi_ip)  # Tự commit; lỗi giới hạn ném ra
    token, bam_token = generate_token()

    try:
        user = find_user_by_email(db, email)
        if user is None or user["email_xac_minh_luc"] is not None:
            raise AlreadyVerifiedError()
        # Cấp token mới, đồng thời vô hiệu liên kết cũ chưa dùng
        issue_account_token(db, user["ma_nguoi_dung"], "xac_minh_email", bam_token, AUTH_TOKEN_TTL_MINUTES)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ma_nguoi_dung": user["ma_nguoi_dung"], "email": user["email"], "ho_ten": user["ho_ten"], "token": token}
