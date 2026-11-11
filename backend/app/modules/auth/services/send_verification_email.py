from html import escape
from urllib.parse import urlencode

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES, FRONTEND_URL
from app.integrations.email.smtp_sender import send_email

VERIFY_PATH = "/xac-minh-email"


def build_verification_link(token: str) -> str:
    return f"{FRONTEND_URL}{VERIFY_PATH}?{urlencode({'token': token})}"


def send_verification_email(to_address: str, ho_ten: str, token: str) -> None:
    """Gửi liên kết xác minh. Lỗi gửi được ném ra dưới dạng EmailSendError."""
    link = build_verification_link(token)
    subject = "HSK AI - Xác minh địa chỉ email"
    text_body = (
        f"Chào {ho_ten},\n\n"
        "Bạn vừa đăng ký tài khoản HSK AI. Mở liên kết sau để xác minh email:\n"
        f"{link}\n\n"
        f"Liên kết có hiệu lực {AUTH_TOKEN_TTL_MINUTES} phút và chỉ dùng được một lần.\n"
        "Nếu bạn không đăng ký, hãy bỏ qua email này."
    )
    html_body = (
        f"<p>Chào {escape(ho_ten)},</p>"
        "<p>Bạn vừa đăng ký tài khoản HSK AI. Bấm nút dưới đây để xác minh email:</p>"
        f'<p><a href="{escape(link)}">Xác minh email</a></p>'
        f"<p>Liên kết có hiệu lực {AUTH_TOKEN_TTL_MINUTES} phút và chỉ dùng được một lần.</p>"
        "<p>Nếu bạn không đăng ký, hãy bỏ qua email này.</p>"
    )
    send_email(to_address, subject, text_body, html_body)