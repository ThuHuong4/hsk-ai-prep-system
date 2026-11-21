"""Thêm câu ví dụ (chữ Hán, pinyin, dịch) cho từ vựng đã có, từ tệp JSON trong scripts/data.

Cách dùng (trong thư mục backend):  python scripts/them_vi_du_tu_vung.py scripts/data/vi_du_tu_vung_hsk1.json

- Câu ví dụ do Xianglingo tự soạn, chỉ dùng từ trong phạm vi cấp đó.
- Chỉ điền cho từ đã có (khớp chữ Hán + pinyin) và CHƯA có ví dụ; từ Giảng viên đã nhập ví dụ thì giữ nguyên.
- Không tạo từ mới, không đổi cấu trúc CSDL (dùng các cột vd_cau, vd_pinyin, vd_nghia sẵn có).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/them_vi_du_tu_vung.py scripts/data/<tệp>.json")
        return 1
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    db = SessionLocal()
    added = kept = missing = 0
    try:
        for row in data["vi_du"]:
            word = db.execute(text("SELECT id, vd_cau FROM tu_vung WHERE chu_han = :h AND pinyin = :p"),
                              {"h": row["chu_han"], "p": row["pinyin"]}).mappings().first()
            if word is None:
                missing += 1
                continue
            if word["vd_cau"]:
                kept += 1
                continue
            db.execute(text("UPDATE tu_vung SET vd_cau = :c, vd_pinyin = :py, vd_nghia = :n WHERE id = :id AND vd_cau IS NULL"),
                       {"c": row["vd_cau"], "py": row["vd_pinyin"], "n": row["vd_nghia"], "id": word["id"]})
            added += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"→ Thêm ví dụ cho {added} từ; giữ nguyên {kept} từ đã có ví dụ; {missing} từ chưa có trong CSDL (bỏ qua).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
