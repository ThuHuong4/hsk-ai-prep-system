"""Nạp thêm thửa Ôn luyện Từ vựng từ một tệp JSON trong scripts/data, dưới tên một tài khoản Giảng viên.

Cách dùng (trong thư mục backend):
    python scripts/seed_tu_vung.py scripts/data/tu_vung_hsk1_them.json <email Giảng viên>
    python scripts/seed_tu_vung.py scripts/data/tu_vung_hsk2_them.json <email Giảng viên>

- Từ lấy theo danh sách từ vựng HSK (hệ HSK 2.0); nghĩa tiếng Việt và câu hỏi do Xianglingo tự soạn.
- Mỗi thửa: Bài 1–4 (5 câu: nhìn từ chọn nghĩa) + Kiểm tra cuối thửa (10 câu: nhìn nghĩa chọn từ), đúng mục 4.1.
- Câu chỉ dùng cho Ôn luyện, mỗi câu gắn một từ (mục 4.3); từ chưa có thì tạo và xuất bản, đã có thì dùng lại.
- Kiểm tra toàn bộ trước khi ghi: từ đã có nhưng thuộc cấp khác thì dừng, không ghi gì.
- Thửa cùng tên đã có ở cấp đó (Từ vựng) thì bỏ qua, không nạp trùng.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.modules.practice_authoring.services import path_service  # noqa: E402
from app.modules.questions.schemas.question_payload import QuestionIn  # noqa: E402
from app.modules.questions.services.question_status import publish_question  # noqa: E402
from app.modules.questions.services.save_question import create_question  # noqa: E402


def place(options: list[str], slot: int) -> tuple[list[str], int]:
    """Phương án đúng (options[0]) đưa tới vị trí slot để đáp án không luôn là A."""
    others = options[1:]
    others.insert(slot % len(options), options[0])
    return others, slot % len(options)


def mc(opts: list[str], answer: int) -> list[dict]:
    return [{"noi_dung": o, "la_dap_an_dung": i == answer} for i, o in enumerate(opts)]


def check_data(data: dict) -> None:
    for land in data["thua"]:
        if len(land["bai"]) != 4 or any(len(words) != 5 for _, words in land["bai"]):
            raise SystemExit(f"✗ Thửa “{land['ten']}” phải có 4 bài × 5 từ")
        meanings = [w[2] for _, words in land["bai"] for w in words]
        if len(set(meanings)) != len(meanings):
            raise SystemExit(f"✗ Thửa “{land['ten']}” có hai từ trùng nghĩa, câu hỏi sẽ có hai đáp án đúng")


def check_words(db, level: int, lands: list[dict]) -> None:
    """Dừng trước khi ghi nếu có từ đã tồn tại ở cấp khác (không sửa dữ liệu sẵn có)."""
    clash = []
    for land in lands:
        for _, words in land["bai"]:
            for h, p, _ in words:
                cap = db.execute(text("SELECT cap_do_id FROM tu_vung WHERE chu_han = :h AND pinyin = :p"),
                                 {"h": h, "p": p}).scalar_one_or_none()
                if cap is not None and cap != level:
                    clash.append(f"{h} ({p})")
    if clash:
        raise SystemExit(f"✗ Các từ đã có nhưng thuộc cấp khác: {', '.join(clash)}. Chưa nạp gì.")


def word_id(db, level: int, uid: int, han: str, py: str, nghia: str, created: list) -> int:
    row = db.execute(text("SELECT id, trang_thai FROM tu_vung WHERE chu_han = :h AND pinyin = :p"),
                     {"h": han, "p": py}).mappings().first()
    if row:
        if row["trang_thai"] != "xuat_ban":
            print(f"  ! Từ {han} đã có nhưng chưa xuất bản: thẻ lật sẽ không hiện từ này cho tới khi bạn xuất bản")
        return int(row["id"])
    result = db.execute(
        text("INSERT INTO tu_vung (chu_han, pinyin, nghia, cap_do_id, trang_thai, nguoi_tao_id) VALUES (:h, :p, :n, :c, 'xuat_ban', :u)"),
        {"h": han, "p": py, "n": nghia, "c": level, "u": uid},
    )
    created.append(han)
    return int(result.lastrowid)


def new_question(db, uid: int, payload: dict) -> int:
    qid = create_question(db, QuestionIn(**payload), uid)
    publish_question(db, qid)
    return qid


def land_exists(db, level: int, name: str) -> bool:
    return bool(db.execute(
        text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'tu_vung' AND ten = :t LIMIT 1"),
        {"c": level, "t": name},
    ).first())


def seed_land(db, uid: int, level: int, cap: str, land: dict) -> None:
    created: list[str] = []
    words = [[(word_id(db, level, uid, h, p, n, created), h, p, n) for h, p, n in ws] for _, ws in land["bai"]]
    db.commit()
    base = {"dang": "chon_mot", "cap_do_id": level, "ky_nang": "tu_vung", "dung_on_luyen": True, "dung_thi_thu": False}
    lessons, n = [], 0
    for (name, _), group in zip(land["bai"], words):
        qids = []
        for i, (wid, h, p, nghia) in enumerate(group):
            opts, ans = place([nghia, group[(i + 1) % 5][3], group[(i + 2) % 5][3]], n)
            n += 1
            qids.append(new_question(db, uid, {
                **base, "tu_vung_id": wid, "noi_dung": h, "pinyin": p.replace(" ", ""), "dich_nghia": f"{h} ({p}): {nghia}",
                "giai_thich": f"{h} đọc là {p}, nghĩa là “{nghia}”.", "phuong_an": mc(opts, ans),
            }))
        lessons.append((name, qids))
    flat = [w for group in words for w in group]
    final = []
    for k, idx in enumerate([0, 2, 5, 7, 10, 12, 15, 17, 3, 8]):
        wid, h, p, nghia = flat[idx]
        a, b = flat[(idx + 6) % 20], flat[(idx + 13) % 20]
        opts, ans = place([f"{h} [{p}]", f"{a[1]} [{a[2]}]", f"{b[1]} [{b[2]}]"], k + 1)
        final.append(new_question(db, uid, {
            **base, "tu_vung_id": wid, "noi_dung": f"Từ nào có nghĩa là “{nghia}”?", "dich_nghia": f"{h} ({p}): {nghia}",
            "giai_thich": f"“{nghia}” là {h} ({p}).", "phuong_an": mc(opts, ans),
        }))
    land_id = path_service.create_land(db, SimpleNamespace(cap_do_id=level, ky_nang="tu_vung", ten=land["ten"],
                                                           muc_tieu=land["muc_tieu"]), uid)
    for pos, (name, qids) in enumerate(lessons + [("Kiểm tra cuối thửa", final)], start=1):
        lesson_id = path_service.create_lesson(db, SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=name,
                                                                   muc_tieu=None, tai_lieu_id=None), uid)
        path_service.set_lesson_items(db, lesson_id, [SimpleNamespace(cau_hoi_id=q) for q in qids])
        path_service.lesson_status(db, lesson_id, "dang")
    path_service.land_status(db, land_id, "dang")
    extra = f" (+ {len(created)} từ mới)" if created else ""
    print(f"→ Từ vựng {cap} · {land['ten']}: 20 câu bài + 10 câu cuối thửa, đã đăng{extra}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Cách dùng: python scripts/seed_tu_vung.py scripts/data/<tệp>.json <email Giảng viên>")
        return 1
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    check_data(data)
    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[2].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        level = db.execute(text("SELECT id FROM cap_do WHERE ma = :m"), {"m": data["cap"]}).scalar_one_or_none()
        if level is None:
            print(f"✗ Chưa có cấp {data['cap']} trong bảng cap_do")
            return 1
        todo = []
        for land in data["thua"]:
            if land_exists(db, level, land["ten"]):
                print(f"· Bỏ qua Từ vựng {data['cap']} · {land['ten']} (đã có)")
            else:
                todo.append(land)
        check_words(db, level, todo)
        db.rollback()
        for land in todo:
            seed_land(db, uid, level, data["cap"], land)
        print("Xong.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
