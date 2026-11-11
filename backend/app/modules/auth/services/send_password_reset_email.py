from html import escape
from urllib.parse import urlencode

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES, FRONTEND_URL
from app.integrations.email.smtp_sender import send_email

RESET_PATH = "/dat-lai-mat-khau"
LOGIN_PATH = "/dang-nhap"


def build_reset_link(token: str) -> str:
    return f"{FRONTEND_URL}{RESET_PATH}?{urlencode({'token': token})}"


def send_password_reset_email(to_address: str, ho_ten: str, token: str) -> None:
    """Gửi liên kết đặt lại mật khẩu. Lỗi gửi được ném ra dưới dạng EmailSendError."""
    link = build_reset_link(token)
    subject = "HSK AI - Đặt lại mật khẩu"
    text_body = (
        f"Chào {ho_ten},\n\n"
        "Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản HSK AI của bạn. "
        "Mở liên kết sau để đặt mật khẩu mới:\n"
        f"{link}\n\n"
        f"Liên kết có hiệu lực {AUTH_TOKEN_TTL_MINUTES} phút và chỉ dùng được một lần.\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên."
    )
    html_body = (
        f"<p>Chào {escape(ho_ten)},</p>"
        "<p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản HSK AI của bạn.</p>"
        f'<p><a href="{escape(link)}">Đặt mật khẩu mới</a></p>'
        f"<p>Liên kết có hiệu lực {AUTH_TOKEN_TTL_MINUTES} phút và chỉ dùng được một lần.</p>"
        "<p>Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên.</p>"
    )
    send_email(to_address, subject, text_body, html_body)


def send_google_account_notice(to_address: str, ho_ten: str) -> None:
    """Tài khoản chỉ dùng Google: hướng dẫn đăng nhập Google, không có liên kết đặt mật khẩu."""
    login_link = f"{FRONTEND_URL}{LOGIN_PATH}"
    subject = "HSK AI - Hướng dẫn đăng nhập"
    text_body = (
        f"Chào {ho_ten},\n\n"
        "Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho email này. "
        "Tài khoản HSK AI của bạn được tạo bằng Google và không dùng mật khẩu riêng.\n"
        f"Hãy mở {login_link} và chọn Đăng nhập với Google.\n\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này."
    )
    html_body = (
        f"<p>Chào {escape(ho_ten)},</p>"
        "<p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho email này. "
        "Tài khoản HSK AI của bạn được tạo bằng Google và không dùng mật khẩu riêng.</p>"
        f'<p>Hãy mở <a href="{escape(login_link)}">trang đăng nhập</a> và chọn '
        "<b>Đăng nhập với Google</b>.</p>"
        "<p>Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>"
    )
    send_email(to_address, subject, text_body, html_body)