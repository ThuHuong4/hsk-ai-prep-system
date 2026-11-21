import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES
from app.database.integrity import is_duplicate_key
from app.integrations.email.smtp_sender import EmailSendError
from app.modules.auth.repositories.create_user import create_student
from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.modules.auth.repositories.save_account_token import issue_account_token
from app.modules.auth.services.enforce_request_limit import check_and_record_request
from app.modules.auth.services.send_verification_email import send_verification_email
from app.security.email_identity import normalize_email
from app.security.one_time_token import generate_token
from app.security.password_hasher import hash_password
from app.security.roles import SELF_SIGNUP_ROLE

logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


def register_user(db: Session, ho_ten: str, email: str, password: str, dia_chi_ip: str) -> dict:
    """Đăng ký xong dùng được ngay; email xác minh gửi kèm, xác minh sau.
    Trả {"user", "gui_email"}; "gui_email" là dữ liệu nội bộ để gửi nền, không trả cho client."""
    email = normalize_email(email)
    check_and_record_request(db, "dang_ky", email, dia_chi_ip)  # Tự commit; lỗi giới hạn ném ra
    mat_khau_bam = hash_password(password)
    token, bam_token = generate_token()

    try:
        if find_user_by_email(db, email) is not None:
            raise EmailAlreadyRegisteredError()
        ma_nguoi_dung = create_student(db, ho_ten, email, mat_khau_bam)
        issue_account_token(db, ma_nguoi_dung, "xac_minh_email", bam_token, AUTH_TOKEN_TTL_MINUTES)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if is_duplicate_key(error, "uq_nguoi_dung_email"):
            raise EmailAlreadyRegisteredError() from error  # Đăng ký đồng thời cùng email
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "user": {
            "ma_nguoi_dung": ma_nguoi_dung,
            "ho_ten": ho_ten,
            "email": email,
            "vai_tro": int(SELF_SIGNUP_ROLE),
            "email_da_xac_minh": False,
        },
        "gui_email": {"ma_nguoi_dung": ma_nguoi_dung, "email": email, "ho_ten": ho_ten, "token": token},
    }


def deliver_verification_email(ma_nguoi_dung: int, email: str, ho_ten: str, token: str) -> None:
    # Chạy nền sau khi đã trả phản hồi; lỗi chỉ ghi log (không ghi token/email)
    try:
        send_verification_email(email, ho_ten, token)
    except EmailSendError as error:
        logger.warning("Gửi email xác minh thất bại, ma_nguoi_dung=%s, loi=%s", ma_nguoi_dung, error)
