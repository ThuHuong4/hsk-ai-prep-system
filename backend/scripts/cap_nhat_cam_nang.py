"""Đăng 10 cẩm nang làm bài (HSK 1–2 Nghe/Đọc, HSK 3–4 Nghe/Đọc/Viết) bản ghi rõ tác giả và nguồn.

Cách dùng (trong thư mục backend):  python scripts/cap_nhat_cam_nang.py <email Giảng viên>

- Chưa có tài liệu cùng tên → tạo mới và đăng.
- Đã có (đang đăng hoặc đã ẩn) → tạo phiên bản mới với tệp PDF mới + nguồn mới rồi đăng
  (theo đúng quy tắc mục 6.5: không ghi đè tệp cũ, bản cũ chuyển đã ẩn). Chạy lại nhiều lần vẫn an toàn.
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
SOURCE = "Nhóm Xianglingo biên soạn; cấu trúc đề theo phần giới thiệu kỳ thi trong đề mẫu HSK của 国家汉办/孔子学院总部 (Hanban)"


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/cap_nhat_cam_nang.py <email Giảng viên>")
        return 1
    items = json.loads((DATA / "cam_nang.json").read_text(encoding="utf-8"))
    missing = [i["tep"] for i in items if not (DATA / i["tep"]).is_file()]
    if missing:
        print(f"✗ Thiếu tệp: {', '.join(missing)}. Chưa làm gì.")
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
            latest = db.execute(
                text("""SELECT t.id FROM tai_lieu t WHERE t.ten = :t
                        ORDER BY t.ma_goc_id DESC, t.phien_ban DESC LIMIT 1"""), {"t": item["ten"]}).scalar_one_or_none()
            db.rollback()
            relative = save_document((DATA / item["tep"]).read_bytes(), "pdf")
            body = MaterialIn(ten=item["ten"], mo_ta=item["mo_ta"], nguon=SOURCE, cap_do_id=levels[item["cap"]],
                              ky_nang=item["ky_nang"], duong_dan=relative)
            try:
                new_id = (material_service.create_material(db, body, uid) if latest is None
                          else material_service.update_material(db, latest, body, uid))
            except Exception:
                delete_file(relative)  # chưa tạo được dòng tài liệu → xóa tệp vừa sao
                raise
            material_service.change_status(db, new_id, "dang")
            print(f"→ Đã đăng “{item['ten']}”" + (" (tạo mới)" if latest is None else " (phiên bản mới)"))
        print("Xong.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
