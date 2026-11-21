"""Quản trị viên thêm Giảng viên: tạo tài khoản + gửi email đặt mật khẩu.

- Quản trị viên chỉ nhập họ tên, email; không biết và không đặt mật khẩu của Giảng viên.
- nguoi_dung bắt buộc có mật khẩu hoặc Google → lưu băm của một mật khẩu ngẫu nhiên không ai biết;
  Giảng viên đặt mật khẩu thật qua liên kết (dùng lại cơ chế Đặt lại mật khẩu: token một lần, có hạn,
  đặt xong tự đánh dấu email đã xác minh).
- Ghi nhat_ky_quan_tri hành động 'tao_tai_khoan' (cần chạy SQL thêm giá trị ENUM).
- Không ghi token hay email vào log.
"""
import logging
import secrets
from html import escape

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES
from app.database.integrity import is_duplicate_key
from app.integrations.email.smtp_sender import EmailSendError, send_email
from app.modules.auth.repositories.find_user_by_email import find_user_by_email
from app.modules.auth.repositories.save_account_token import issue_account_token
from app.modules.auth.services.send_password_reset_email import build_reset_link
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.security.email_identity import normalize_email
from app.security.one_time_token import generate_token
from app.security.password_hasher import hash_password
from app.security.roles import Role

logger = logging.getLogger(__name__)
PURPOSE = "dat_lai_mat_khau"


def _send_invite(email: str, ho_ten: str, token: str) -> bool:
    link = build_reset_link(token)
    text_body = (
        f"Chào {ho_ten},\n\n"
        "Quản trị viên Xianglingo đã tạo cho bạn tài khoản Giảng viên. "
        "Mở liên kết sau để tự đặt mật khẩu và đăng nhập:\n"
        f"{link}\n\n"
        f"Liên kết có hiệu lực {AUTH_TOKEN_TTL_MINUTES} phút và chỉ dùng được một lần. "
        "Hết hạn thì nhờ Quản trị viên gửi lại, hoặc dùng Quên mật khẩu ở trang đăng nhập."
    )
    html_body = (
        f"<p>Chào {escape(ho_ten)},</p>"
        "<p>Quản trị viên Xianglingo đã tạo cho bạn tài khoản <b>Giảng viên</b>.</p>"
        f'<p><a href="{escape(link)}">Đặt mật khẩu và đăng nhập</a></p>'
        f"<p>Liên kết có hiệu lực {AUTH_TOKEN_TTL_MINUTES} phút và chỉ dùng được một lần. "
        "Hết hạn thì nhờ Quản trị viên gửi lại, hoặc dùng Quên mật khẩu ở trang đăng nhập.</p>"
    )
    try:
        send_email(email, "Xianglingo - Tài khoản Giảng viên của bạn", text_body, html_body)
        return True
    except EmailSendError as error:
        logger.warning("Gửi email mời Giảng viên thất bại, loi=%s", error)
        return False


def create_lecturer(db: Session, admin_id: int, ho_ten: str, email: str) -> dict:
    email = normalize_email(email)
    token, token_hash = generate_token()
    random_hash = hash_password(secrets.token_urlsafe(32))  # không ai biết, chỉ để thỏa ràng buộc
    try:
        existing = find_user_by_email(db, email)
        if existing is not None:
            raise ConflictError("Email đã có tài khoản. Nếu là Học viên, dùng nút \"Đổi thành Giảng viên\".")
        result = db.execute(
            text("""INSERT INTO nguoi_dung (vai_tro_id, email, ho_ten, mat_khau_bam, trang_thai, ks_trang_thai)
                    VALUES (:v, :e, :h, :m, 'hoat_dong', 'bo_qua')"""),
            {"v": int(Role.GIANG_VIEN), "e": email, "h": ho_ten, "m": random_hash},
        )
        user_id = int(result.lastrowid)
        issue_account_token(db, user_id, PURPOSE, token_hash, AUTH_TOKEN_TTL_MINUTES)
        db.execute(
            text("""INSERT INTO nhat_ky_quan_tri (nguoi_thao_tac_id, nguoi_bi_tac_dong_id, hanh_dong, ly_do)
                    VALUES (:a, :u, 'tao_tai_khoan', 'Tạo tài khoản Giảng viên')"""),
            {"a": admin_id, "u": user_id},
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if is_duplicate_key(error, "uq_nguoi_dung_email"):
            raise ConflictError("Email đã có tài khoản") from error
        raise
    except Exception:
        db.rollback()
        raise
    sent = _send_invite(email, ho_ten, token)
    return {"id": user_id, "da_gui_email": sent,
            "message": "Đã tạo tài khoản Giảng viên và gửi email đặt mật khẩu" if sent
            else "Đã tạo tài khoản nhưng chưa gửi được email. Bấm \"Gửi lại email\" sau."}


def resend_invite(db: Session, admin_id: int, user_id: int) -> dict:
    if user_id == admin_id:
        raise RuleError("Không tự sửa tài khoản của mình")
    token, token_hash = generate_token()
    try:
        row = db.execute(
            text("SELECT id, email, ho_ten, vai_tro_id, trang_thai, mat_khau_bam IS NOT NULL AS co_mk FROM nguoi_dung WHERE id = :id FOR UPDATE"),
            {"id": user_id},
        ).mappings().first()
        if row is None:
            raise NotFoundError()
        if row["vai_tro_id"] != int(Role.GIANG_VIEN):
            raise RuleError("Chỉ gửi email đặt mật khẩu cho tài khoản Giảng viên")
        if row["trang_thai"] != "hoat_dong":
            raise RuleError("Tài khoản đang bị khóa")
        if not row["co_mk"]:
            raise RuleError("Tài khoản này đăng nhập bằng Google")
        issue_account_token(db, user_id, PURPOSE, token_hash, AUTH_TOKEN_TTL_MINUTES)
        db.commit()
    except Exception:
        db.rollback()
        raise
    sent = _send_invite(row["email"], row["ho_ten"], token)
    if not sent:
        raise RuleError("Chưa gửi được email, kiểm tra cấu hình SMTP rồi thử lại")
    return {"message": "Đã gửi lại email đặt mật khẩu"}
