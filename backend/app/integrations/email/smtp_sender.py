import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.mail_config import (
    MAIL_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TIMEOUT_SECONDS,
    SMTP_USER,
)


class EmailSendError(Exception):
    """Gửi email thất bại; chỉ mang tên loại lỗi, không mang thông tin bí mật."""


def _build_message(to_address: str, subject: str, text_body: str, html_body: str | None) -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((MAIL_FROM_NAME, SMTP_USER))
    message["To"] = to_address
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=SMTP_USER.rsplit("@", 1)[-1])
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def send_email(to_address: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    context = ssl.create_default_context()
    try:
        message = _build_message(to_address, subject, text_body, html_body)
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS, context=context
            ) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)
    except (smtplib.SMTPException, OSError, ValueError) as error:
        raise EmailSendError(type(error).__name__) from error