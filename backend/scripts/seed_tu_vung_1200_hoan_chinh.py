"""Hoàn thiện kho từ điển Tra từ HSK 1–4 (≥ 1.200 từ xuất bản, 100% có ví dụ song ngữ).

- Cập nhật câu ví dụ (vd_cau, vd_pinyin, vd_nghia) cho toàn bộ 196 từ HSK 3 chưa có ví dụ.
- Bổ sung từ HSK 3 còn thiếu (đạt ≥ 300 từ HSK 3) và 480+ từ HSK 4 chuẩn hệ HSK 2.0 (đạt ≥ 600 từ HSK 4).
- An toàn khi chạy lại nhiều lần (idempotent).
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.search.services import search_service

DATA_DIR = Path(__file__).resolve().parent / "data"


def _validate_entry(w: dict, require_cap: bool = True) -> None:
    fields = ("chu_han", "pinyin", "nghia", "vd_cau", "vd_pinyin", "vd_nghia") + (("cap",) if require_cap else ())
    for f in fields:
        if not str(w.get(f) or "").strip():
            raise ValueError(f"Thiếu trường '{f}' ở mục từ: {w}")


def main() -> int:
    hsk3_file = DATA_DIR / "tu_vung_hsk3_vi_du_bo_sung.json"
    hsk4_p1_file = DATA_DIR / "tu_vung_hsk4_phan_1.json"
    hsk4_p2_file = DATA_DIR / "tu_vung_hsk4_phan_2.json"

    for fp in (hsk3_file, hsk4_p1_file, hsk4_p2_file):
        if not fp.is_file():
            print(f"✗ Chưa tìm thấy tệp dữ liệu: {fp}")
            return 1

    hsk3_data = json.loads(hsk3_file.read_text(encoding="utf-8"))
    hsk4_p1 = json.loads(hsk4_p1_file.read_text(encoding="utf-8"))
    hsk4_p2 = json.loads(hsk4_p2_file.read_text(encoding="utf-8"))

    db = SessionLocal()
    try:
        uid = db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one()
        levels = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}

        # 1. Cập nhật câu ví dụ cho các từ HSK 3 đang trống vd_cau
        updated_ex = 0
        for item in hsk3_data.get("cap_nhat_vi_du", []):
            for f in ("chu_han", "vd_cau", "vd_pinyin", "vd_nghia"):
                if not str(item.get(f) or "").strip():
                    raise ValueError(f"Thiếu trường '{f}' khi cập nhật ví dụ: {item}")
            res = db.execute(
                text("""
                    UPDATE tu_vung
                    SET vd_cau = :vc, vd_pinyin = :vp, vd_nghia = :vn
                    WHERE id = :id AND chu_han = :h AND (vd_cau IS NULL OR vd_cau = '')
                """),
                {
                    "id": int(item["id"]),
                    "h": item["chu_han"].strip(),
                    "vc": item["vd_cau"].strip(),
                    "vp": item["vd_pinyin"].strip(),
                    "vn": item["vd_nghia"].strip(),
                },
            )
            updated_ex += int(res.rowcount or 0)

        # 2. Nạp thêm từ HSK 3 + HSK 4 mới (không trùng chu_han + pinyin)
        existing_pairs = {
            (r[0], r[1].lower())
            for r in db.execute(text("SELECT chu_han, pinyin FROM tu_vung")).all()
        }
        new_pool = (
            list(hsk3_data.get("them_moi_hsk3", []))
            + list(hsk4_p1.get("tu", []))
            + list(hsk4_p2.get("tu", []))
        )

        added: dict[str, int] = {}
        skipped = 0
        for w in new_pool:
            _validate_entry(w, require_cap=True)
            cap = w["cap"].strip()
            han = w["chu_han"].strip()
            py = w["pinyin"].strip()
            key = (han, py.lower())
            if key in existing_pairs:
                skipped += 1
                continue
            db.execute(
                text("""
                    INSERT INTO tu_vung (chu_han, pinyin, nghia, cap_do_id, vd_cau, vd_pinyin, vd_nghia, trang_thai, nguoi_tao_id)
                    VALUES (:h, :p, :n, :c, :vc, :vp, :vn, 'xuat_ban', :u)
                """),
                {
                    "h": han,
                    "p": py,
                    "n": w["nghia"].strip(),
                    "c": levels[cap],
                    "vc": w["vd_cau"].strip(),
                    "vp": w["vd_pinyin"].strip(),
                    "vn": w["vd_nghia"].strip(),
                    "u": uid,
                },
            )
            existing_pairs.add(key)
            added[cap] = added.get(cap, 0) + 1

        db.commit()
        search_service._cache["at"] = 0.0

        summary = db.execute(
            text("""
                SELECT c.ma, COUNT(*) AS tong,
                       SUM(CASE WHEN t.vd_cau IS NOT NULL AND t.vd_cau <> '' THEN 1 ELSE 0 END) AS co_vd
                FROM tu_vung t JOIN cap_do c ON c.id = t.cap_do_id
                WHERE t.trang_thai = 'xuat_ban'
                GROUP BY c.ma, c.thu_tu ORDER BY c.thu_tu
            """)
        ).mappings().all()
        total_words = sum(int(r["tong"]) for r in summary)
        total_ex = sum(int(r["co_vd"]) for r in summary)
        print(f"→ Đã bổ sung ví dụ cho {updated_ex} từ HSK 3; thêm mới {added} (bỏ qua {skipped} trùng).")
        for r in summary:
            print(f"  · {r['ma']}: {r['tong']} từ ({r['co_vd']} có ví dụ)")
        print(f"→ TỔNG CỘNG: {total_words} từ xuất bản ({total_ex}/{total_words} có câu ví dụ song ngữ).")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
