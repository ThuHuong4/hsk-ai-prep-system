from sqlalchemy.orm import Session

from app.core.auth_config import (
    AUTH_LIMIT_PER_EMAIL_PER_HOUR,
    AUTH_LIMIT_PER_IP_PER_HOUR,
    AUTH_REQUEST_LOG_RETENTION_DAYS,
    AUTH_RESEND_MIN_SECONDS,
)
from app.database.named_lock import named_locks
from app.modules.auth.repositories.auth_request_log import (
    count_ip_requests_last_hour,
    delete_old_auth_requests,
    get_email_request_stats,
    record_auth_request,
)
from app.security.email_identity import email_hmac

PURPOSES = {"dang_ky", "xac_minh_email", "dat_lai_mat_khau", "lien_ket_google"}


class RateLimitedError(Exception):
    def __init__(self, retry_after_seconds: int | None):
        super().__init__("Vượt giới hạn yêu cầu")
        self.retry_after_seconds = retry_after_seconds


def check_and_record_request(
    db: Session,
    muc_dich: str,
    email: str,
    dia_chi_ip: str,
    *,
    min_interval_seconds: int | None = None,
    email_limit_per_hour: int | None = None,
    ip_limit_per_hour: int | None = None,
) -> None:
    """Kiểm tra giới hạn rồi ghi nhận yêu cầu. Hàm này commit Session,
    nên phải được gọi TRƯỚC mọi thao tác ghi khác của request.
    Không truyền tham số giới hạn thì dùng mức mặc định của các luồng gửi email."""
    if muc_dich not in PURPOSES:
        raise ValueError("Mục đích không hợp lệ")

    min_interval = AUTH_RESEND_MIN_SECONDS if min_interval_seconds is None else min_interval_seconds
    email_limit = AUTH_LIMIT_PER_EMAIL_PER_HOUR if email_limit_per_hour is None else email_limit_per_hour
    ip_limit = AUTH_LIMIT_PER_IP_PER_HOUR if ip_limit_per_hour is None else ip_limit_per_hour

    bam_email = email_hmac(email)
    keys = [f"email:{muc_dich}:{bam_email.hex()}", f"ip:{muc_dich}:{dia_chi_ip}"]

    with named_locks(keys):
        try:
            stats = get_email_request_stats(db, muc_dich, bam_email)
            seconds_since_last = stats["giay_tu_lan_cuoi"]
            if min_interval > 0 and seconds_since_last is not None and seconds_since_last < min_interval:
                raise RateLimitedError(min_interval - seconds_since_last)
            if stats["so_lan_1_gio"] >= email_limit:
                raise RateLimitedError(None)
            if count_ip_requests_last_hour(db, muc_dich, dia_chi_ip) >= ip_limit:
                raise RateLimitedError(None)

            record_auth_request(db, muc_dich, bam_email, dia_chi_ip)
            db.commit()  # Ghi nhận phải commit trước khi giải phóng khóa
        except Exception:
            db.rollback()
            raise

    _cleanup_old_requests(db)


def _cleanup_old_requests(db: Session) -> None:
    # Dọn theo thời hạn lưu; lỗi dọn dẹp không làm hỏng yêu cầu chính
    try:
        delete_old_auth_requests(db, AUTH_REQUEST_LOG_RETENTION_DAYS)
        db.commit()
    except Exception:
        db.rollback()