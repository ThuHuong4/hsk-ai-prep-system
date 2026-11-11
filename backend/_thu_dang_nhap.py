import sys
import time

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.auth.services.authenticate_user import authenticate_user

verified_email = sys.argv[1]    # tài khoản +hsk2 đã xác minh
unverified_email = sys.argv[2]  # tài khoản +hsk1 chưa xác minh
db = SessionLocal()


def t(label, email, password):
    start = time.perf_counter()
    try:
        r = authenticate_user(db, email, password)
        out = f"OK vai_tro={r['vai_tro']}, co mat_khau_bam={'mat_khau_bam' in r}"
    except Exception as error:
        out = type(error).__name__
    print(label, out, f"({time.perf_counter() - start:.2f}s)")


try:
    t("1 Email khong ton tai:", "khong-co@example.test", "MatKhau123")
    t("2 Sai mat khau:", "hocvien1@example.test", "SaiMatKhau1")
    t("3 Dung:", "hocvien1@example.test", "HskDemo2026!")
    t("4 Viet hoa + khoang trang:", "  HocVien1@Example.TEST ", "HskDemo2026!")
    t("5 Da xac minh (+hsk2):", verified_email, "MatKhau123")
    t("6 Chua xac minh, dung mat khau:", unverified_email, "MatKhau123")
    t("7 Chua xac minh, sai mat khau:", unverified_email, "SaiMatKhau1")
    db.execute(
        text("UPDATE nguoi_dung SET mat_khau_bam = NULL WHERE email = :e"),
        {"e": verified_email.strip().lower()},
    )
    t("8 Tai khoan chi dung Google:", verified_email, "MatKhau123")
finally:
    db.rollback()
    db.close()