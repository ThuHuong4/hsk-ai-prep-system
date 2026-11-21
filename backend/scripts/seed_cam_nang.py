"""Nạp 4 cẩm nang làm bài (HSK 1–2 Nghe/Đọc) vào Tài liệu ôn tập, trạng thái đang đăng.

Cách dùng (trong thư mục backend):  python scripts/seed_cam_nang.py <email Giảng viên>

- Tệp PDF trong scripts/data/cam_nang được sao vào private_uploads/documents (không ghi đè tệp nào).
- Tạo và đăng bằng chính quy tắc của mục Tài liệu (material_service): kiểm tra tệp, cấp độ, kích thước.
- Tài liệu cùng tên đã có thì bỏ qua, không nạp trùng.
- Nguồn: Xianglingo tự soạn; cấu trúc đề theo đề HSK 2.0 chính thức.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.modules.materials.endpoints.lecturer_materials import MaterialIn  # noqa: E402
from app.modules.materials.services import material_service  # noqa: E402
from app.storage.private_files import delete_file, save_document  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "cam_nang"
SOURCE = "Xianglingo tự soạn; cấu trúc đề theo đề HSK 2.0 (国家汉办/孔子学院总部)"


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/seed_cam_nang.py <email Giảng viên>")
        return 1
    items = json.loads((DATA / "cam_nang.json").read_text(encoding="utf-8"))
    missing = [i["tep"] for i in items if not (DATA / i["tep"]).is_file()]
    if missing:
        print(f"✗ Thiếu tệp: {', '.join(missing)}. Chưa nạp gì.")
        return 1
    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[1].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        levels = {m: i for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}
        db.rollback()
        for item in items:
            if item["cap"] not in levels:
                print(f"✗ Chưa có cấp {item['cap']}, bỏ qua {item['ten']}")
                continue
            if db.execute(text("SELECT 1 FROM tai_lieu WHERE ten = :t LIMIT 1"), {"t": item["ten"]}).first():
                db.rollback()
                print(f"· Bỏ qua “{item['ten']}” (đã có)")
                continue
            db.rollback()
            relative = save_document((DATA / item["tep"]).read_bytes(), "pdf")
            try:
                body = MaterialIn(ten=item["ten"], mo_ta=item["mo_ta"], nguon=SOURCE, cap_do_id=levels[item["cap"]],
                                  ky_nang=item["ky_nang"], duong_dan=relative)
                new_id = material_service.create_material(db, body, uid)
            except Exception:
                delete_file(relative)  # chưa tạo được dòng tài liệu → xóa tệp vừa sao
                raise
            material_service.change_status(db, new_id, "dang")
            print(f"→ Đã đăng tài liệu “{item['ten']}”")
        print("Xong.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
