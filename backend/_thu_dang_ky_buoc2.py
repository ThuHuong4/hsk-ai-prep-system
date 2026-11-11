import sys

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.auth.schemas.register_request import RegisterRequest
from app.modules.auth.services.enforce_request_limit import RateLimitedError
from app.modules.auth.services.register_user import deliver_verification_email, register_user

email = sys.argv[1]
IP = "203.0.113.50"  # IP kiểm thử


def run(label, address):
    db = SessionLocal()
    try:
        r = register_user(db, "Học viên thử", address, "MatKhau123", IP)
        print(label, "-> co gui email" if r["gui_email"] else "-> khong gui email")
        if r["gui_email"]:
            deliver_verification_email(**r["gui_email"])
        return r["message"]
    except RateLimitedError as error:
        print(label, "-> RateLimited, cho", error.retry_after_seconds, "giay")
    finally:
        db.close()


m1 = run("1 Email moi:", email)
run("2 Gui lai ngay:", email)
m3 = run("3 Email da co:", "hocvien1@example.test")
m4 = run("4 Email da co, viet hoa + khoang trang:", "  HocVien2@Example.TEST ")
print("5 Thong bao giong nhau:", m1 == m3 == m4)

db = SessionLocal()
row = db.execute(
    text("""SELECT vai_tro, trang_thai, email_xac_minh_luc, mat_khau_bam LIKE 'pbkdf2_sha256$%' AS da_bam
            FROM nguoi_dung WHERE email = :e"""),
    {"e": email.strip().lower()},
).mappings().one()
print("6 Tai khoan:", dict(row))
db.close()

for bad in [{"ho_ten": " ", "email": "a@b.com", "password": "MatKhau123"},
            {"ho_ten": "A", "email": "khong-hop-le", "password": "MatKhau123"},
            {"ho_ten": "A", "email": "a@b.com", "password": "chiCoChu"},
            {"ho_ten": "A", "email": "a@b.com", "password": "MatKhau123", "vai_tro": 2}]:
    try:
        RegisterRequest(**bad)
        print("7 SAI: chap nhan", bad)
    except ValueError:
        print("7 Tu choi dung:", list(bad)[-1] if "vai_tro" in bad else bad)