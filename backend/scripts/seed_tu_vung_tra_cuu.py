"""Bổ sung từ vựng để Tra từ đủ HSK 1–3 (hệ HSK 2.0): 22 hư từ HSK 1–2 (có ví dụ) và khoảng 240 từ HSK 3.

Cách dùng (trong thư mục backend):
    python scripts/seed_tu_vung_tra_cuu.py scripts/data/tu_vung_tra_cuu_hsk123.json <email Giảng viên>

- Từ được tạo ở trạng thái xuất bản → hiện ngay trong Tra từ và trang Từ vựng của Giảng viên.
- Không gắn vào bài/thửa nào nên không xuất hiện trong bài Ôn luyện hay thẻ lật.
- Từ đã có (cùng chữ Hán + pinyin, ở bất kỳ cấp nào) thì bỏ qua, không sửa.
- Nghĩa và ví dụ do Xianglingo tự soạn; Giảng viên có thể sửa trong trang Từ vựng.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("Cách dùng: python scripts/seed_tu_vung_tra_cuu.py scripts/data/<tệp>.json <email Giảng viên>")
        return 1
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[2].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        levels = {m: i for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}
        missing_levels = sorted({t["cap"] for t in data["tu"]} - set(levels))
        if missing_levels:
            print(f"✗ Chưa có cấp {', '.join(missing_levels)} trong bảng cap_do. Chưa nạp gì.")
            return 1
        added, skipped = {}, 0
        for t in data["tu"]:
            if db.execute(text("SELECT 1 FROM tu_vung WHERE chu_han = :h AND pinyin = :p"),
                          {"h": t["chu_han"], "p": t["pinyin"]}).first():
                skipped += 1
                continue
            db.execute(
                text("""INSERT INTO tu_vung (chu_han, pinyin, nghia, cap_do_id, vd_cau, vd_pinyin, vd_nghia, trang_thai, nguoi_tao_id)
                        VALUES (:h, :p, :n, :c, :vc, :vp, :vn, 'xuat_ban', :u)"""),
                {"h": t["chu_han"], "p": t["pinyin"], "n": t["nghia"], "c": levels[t["cap"]],
                 "vc": t.get("vd_cau"), "vp": t.get("vd_pinyin"), "vn": t.get("vd_nghia"), "u": uid},
            )
            added[t["cap"]] = added.get(t["cap"], 0) + 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    detail = ", ".join(f"{k}: {v}" for k, v in sorted(added.items())) or "0"
    print(f"→ Đã thêm từ ({detail}); bỏ qua {skipped} từ đã có.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
