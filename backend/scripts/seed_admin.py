"""Tạo tài khoản Giảng viên / Quản trị viên (chạy tay, trên máy có CSDL).

Cách chạy (đứng trong thư mục backend):
    python scripts/seed_admin.py

Mật khẩu gõ lúc chạy (không hiện ra màn hình), không lưu trong file nào.
"""
import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # để import được gói app

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.security.email_identity import normalize_email  # noqa: E402
from app.security.password_hasher import hash_password  # noqa: E402
from app.security.password_policy import validate_password_strength  # noqa: E402
from app.security.roles import Role  # noqa: E402

ROLES = {"2": Role.QUAN_TRI_VIEN, "3": Role.GIANG_VIEN}
ROLE_NAMES = {Role.QUAN_TRI_VIEN: "Quản trị viên", Role.GIANG_VIEN: "Giảng viên"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
INITIAL_ENERGY = 5


def ask(prompt: str, check) -> str:
    while True:
        value = input(prompt).strip()
        error = check(value)
        if error is None:
            return value
        print(f"  ✗ {error}")


def ask_password() -> str:
    while True:
        password = getpass.getpass("Mật khẩu: ")
        try:
            validate_password_strength(password)
        except ValueError as error:
            print(f"  ✗ {error}")
            continue
        if getpass.getpass("Nhập lại mật khẩu: ") != password:
            print("  ✗ Hai mật khẩu không giống nhau")
            continue
        return password


def main() -> int:
    email = normalize_email(ask("Email: ", lambda v: None if EMAIL_PATTERN.fullmatch(v) else "Email không hợp lệ"))
    ho_ten = ask("Họ tên: ", lambda v: None if 0 < len(v) <= 100 else "Họ tên 1–100 ký tự")
    role = ROLES[ask("Vai trò (2 = Quản trị, 3 = Giảng viên): ", lambda v: None if v in ROLES else "Chỉ nhập 2 hoặc 3")]
    mat_khau_bam = hash_password(ask_password())

    db = SessionLocal()
    try:
        exists = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e"), {"e": email}).first()
        if exists:
            print("✗ Email này đã có tài khoản. Dùng email khác.")
            return 1
        result = db.execute(
            text("""
                INSERT INTO nguoi_dung (vai_tro_id, email, ho_ten, mat_khau_bam, trang_thai, nang_luong)
                VALUES (:vai_tro, :email, :ho_ten, :mat_khau_bam, 'hoat_dong', :nang_luong)
            """),
            {"vai_tro": int(role), "email": email, "ho_ten": ho_ten,
             "mat_khau_bam": mat_khau_bam, "nang_luong": INITIAL_ENERGY},
        )
        # Giữ đối soát năng lượng khớp như tài khoản tự đăng ký
        db.execute(
            text("INSERT INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong) VALUES (:id, 'khoi_tao', :n)"),
            {"id": result.lastrowid, "n": INITIAL_ENERGY},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        print("✗ Không tạo được (email có thể vừa được dùng). Thử lại với email khác.")
        return 1
    finally:
        db.close()

    print(f"→ Đã tạo tài khoản {ROLE_NAMES[role]}: {email}. Đăng nhập trên web bằng email và mật khẩu vừa nhập.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
