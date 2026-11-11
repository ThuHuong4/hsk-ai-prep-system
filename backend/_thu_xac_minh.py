import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth_config import AUTH_TOKEN_TTL_MINUTES
from app.database.session import SessionLocal
from app.modules.auth.repositories.save_account_token import issue_account_token
from app.modules.auth.services.verify_email import verify_email
from app.security.email_identity import normalize_email
from app.security.one_time_token import generate_token

db = SessionLocal()
db.commit = lambda: None    # Giữ mọi thay đổi trong 1 transaction
db.rollback = lambda: None  # để rollback toàn bộ ở cuối


def verified_at(uid):
    return db.execute(
        text("SELECT email_xac_minh_luc FROM nguoi_dung WHERE ma_nguoi_dung = :u"), {"u": uid}
    ).scalar_one()


def t(label, token):
    try:
        verify_email(db, token)
        print(label, "OK")
    except Exception as error:
        print(label, type(error).__name__)


try:
    uid = db.execute(
        text("SELECT ma_nguoi_dung FROM nguoi_dung WHERE email = :e"),
        {"e": normalize_email(sys.argv[1])},
    ).scalar_one()
    print("0 Truoc khi xac minh:", verified_at(uid))

    t1, h1 = generate_token()
    issue_account_token(db, uid, "xac_minh_email", h1, AUTH_TOKEN_TTL_MINUTES)
    t("1 Token hop le:", t1)
    print("  email_xac_minh_luc da co gia tri:", verified_at(uid) is not None)
    t("2 Dung lai token:", t1)
    t("3 Token dung dinh dang nhung khong ton tai:", generate_token()[0])
    t("4 Token sai dinh dang:", "abc")

    t2, h2 = generate_token()
    issue_account_token(db, uid, "xac_minh_email", h2, AUTH_TOKEN_TTL_MINUTES)
    _, h3 = generate_token()
    issue_account_token(db, uid, "xac_minh_email", h3, AUTH_TOKEN_TTL_MINUTES)
    t("5 Token cu da bi thay bang lien ket moi:", t2)
finally:
    Session.rollback(db)
    print("6 Sau rollback, van chua xac minh:", verified_at(uid) is None)
    db.close()