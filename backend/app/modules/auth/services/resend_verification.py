from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_RESEND_MIN_SECONDS, AUTH_TOKEN_TTL_MINUTES
from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.modules.auth.repositories.save_account_token import issue_account_token
from app.modules.auth.services.enforce_request_limit import check_and_record_request
from app.security.email_identity import normalize_email
from app.security.one_time_token import generate_token

ACTIVE = 1  # 1 = Hoạt động, 0 = Khóa

GENERIC_MESSAGE = (
    "Nếu email thuộc một tài khoản chưa xác minh, bạn sẽ nhận được liên kết xác minh mới. "
    "Hãy kiểm tra cả thư mục Spam; nếu chưa nhận được, "
    f"có thể yêu cầu gửi lại sau {AUTH_RESEND_MIN_SECONDS} giây."
)


def resend_verification(db: Session, email: str, dia_chi_ip: str) -> dict:
    """Trả {"message", "gui_email"}; "gui_email" là dữ liệu nội bộ để gửi nền, không trả cho client."""
    email = normalize_email(email)
    check_and_record_request(db, "xac_minh_email", email, dia_chi_ip)  # Tự commit; lỗi giới hạn ném ra
    token, bam_token = generate_token()

    try:
        user = find_user_by_email(db, email)
        can_resend = (
            user is not None
            and user["email_xac_minh_luc"] is None  # Chưa xác minh
            and user["mat_khau_bam"]                # Tài khoản đăng ký bằng mật khẩu
            and user["trang_thai"] == ACTIVE        # Không bị khóa
        )
        if not can_resend:
            db.rollback()
            return {"message": GENERIC_MESSAGE, "gui_email": None}

        # Cấp token mới, đồng thời vô hiệu các liên kết cũ chưa dùng
        issue_account_token(db, user["ma_nguoi_dung"], "xac_minh_email", bam_token, AUTH_TOKEN_TTL_MINUTES)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": GENERIC_MESSAGE,
        "gui_email": {
            "ma_nguoi_dung": user["ma_nguoi_dung"],
            "email": user["email"],
            "ho_ten": user["ho_ten"],
            "token": token,
        },
    }