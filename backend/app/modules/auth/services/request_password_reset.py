import logging

from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_RESEND_MIN_SECONDS, AUTH_TOKEN_TTL_MINUTES
from app.integrations.email.smtp_sender import EmailSendError
from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.modules.auth.repositories.save_account_token import issue_account_token
from app.modules.auth.services.enforce_request_limit import check_and_record_request
from app.modules.auth.services.send_password_reset_email import (
    send_google_account_notice,
    send_password_reset_email,
)
from app.security.email_identity import normalize_email
from app.security.one_time_token import generate_token

logger = logging.getLogger(__name__)

ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa
PURPOSE = "dat_lai_mat_khau"

GENERIC_MESSAGE = (
    "Nếu email phù hợp, bạn sẽ nhận được hướng dẫn đặt lại mật khẩu. "
    "Hãy kiểm tra cả thư mục Spam; nếu chưa nhận được, "
    f"có thể yêu cầu lại sau {AUTH_RESEND_MIN_SECONDS} giây."
)


def request_password_reset(db: Session, email: str, dia_chi_ip: str) -> dict:
    """Trả {"message", "gui_email"}; "gui_email" là dữ liệu nội bộ để gửi nền, không trả cho client."""
    email = normalize_email(email)
    check_and_record_request(db, PURPOSE, email, dia_chi_ip)  # Tự commit; lỗi giới hạn ném ra
    token, bam_token = generate_token()

    try:
        user = find_user_by_email(db, email)
        if user is None or user["trang_thai"] != ACTIVE:
            db.rollback()
            return {"message": GENERIC_MESSAGE, "gui_email": None}

        recipient = {"ma_nguoi_dung": user["ma_nguoi_dung"], "email": user["email"], "ho_ten": user["ho_ten"]}

        if not user["mat_khau_bam"]:
            # Tài khoản chỉ dùng Google: không tạo token, chỉ gửi hướng dẫn
            db.rollback()
            return {"message": GENERIC_MESSAGE, "gui_email": {**recipient, "loai": "google", "token": None}}

        # Cấp token mới, đồng thời vô hiệu các liên kết đặt lại cũ chưa dùng
        issue_account_token(db, user["ma_nguoi_dung"], PURPOSE, bam_token, AUTH_TOKEN_TTL_MINUTES)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"message": GENERIC_MESSAGE, "gui_email": {**recipient, "loai": "dat_lai", "token": token}}


def deliver_password_reset_email(
    loai: str, ma_nguoi_dung: int, email: str, ho_ten: str, token: str | None
) -> None:
    # Chạy nền sau khi đã trả phản hồi; lỗi chỉ ghi log (không ghi token/email)
    try:
        if loai == "google":
            send_google_account_notice(email, ho_ten)
        else:
            send_password_reset_email(email, ho_ten, token)
    except EmailSendError as error:
        logger.warning(
            "Gửi email đặt lại mật khẩu thất bại, ma_nguoi_dung=%s, loai=%s, loi=%s",
            ma_nguoi_dung, loai, error,
        )