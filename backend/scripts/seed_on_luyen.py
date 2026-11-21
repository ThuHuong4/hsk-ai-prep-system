"""Nạp thửa Ôn luyện (Đọc, Viết…) từ một tệp JSON trong scripts/data, dưới tên một tài khoản Giảng viên.

Cách dùng (trong thư mục backend):
    python scripts/seed_on_luyen.py scripts/data/doc_hsk1_them.json <email Giảng viên>
    python scripts/seed_on_luyen.py scripts/data/viet_hsk3.json <email Giảng viên>

- Câu hỏi do Xianglingo tự soạn theo từ vựng và ngữ pháp của cấp; chỉ dùng cho Ôn luyện.
- Mỗi thửa: Bài 1–4 (5 câu) + Kiểm tra cuối thửa (10 câu), đúng mục 4.1.
- Kiểm tra toàn bộ câu theo quy tắc của ngân hàng câu hỏi trước khi ghi; có câu sai thì dừng, không ghi gì.
- Thửa cùng tên đã có ở cấp × kỹ năng đó thì bỏ qua, không nạp trùng.
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
from app.modules.questions.services.question_rules import QuestionRuleError, validate_question  # noqa: E402
from app.modules.questions.services.question_status import publish_question  # noqa: E402
from app.modules.questions.services.save_question import create_question  # noqa: E402

SKILL_NAME = {"nghe": "Nghe", "doc": "Đọc", "viet": "Viết", "tu_vung": "Từ vựng"}


def prepare(item: dict, level: int, skill: str) -> QuestionIn:
    q = QuestionIn(**item, cap_do_id=level, ky_nang=skill, dung_on_luyen=True, dung_thi_thu=False)
    validate_question(q)
    return q


def main() -> int:
    if len(sys.argv) != 3:
        print("Cách dùng: python scripts/seed_on_luyen.py scripts/data/<tệp>.json <email Giảng viên>")
        return 1
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    skill = data["ky_nang"]
    for land in data["thua"]:
        if len(land["bai"]) != 4 or any(len(b["cau"]) != 5 for b in land["bai"]) or len(land["cuoi_thua"]) != 10:
            print(f"✗ Thửa “{land['ten']}” phải có 4 bài × 5 câu và 10 câu cuối thửa")
            return 1
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
        label = f"{SKILL_NAME[skill]} {data['cap']}"
        todo = []
        for land in data["thua"]:
            if db.execute(text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = :k AND ten = :t LIMIT 1"),
                          {"c": level, "k": skill, "t": land["ten"]}).first():
                print(f"· Bỏ qua {label} · {land['ten']} (đã có)")
                continue
            try:
                lessons = [(b["ten"], [prepare(c, level, skill) for c in b["cau"]]) for b in land["bai"]]
                lessons.append(("Kiểm tra cuối thửa", [prepare(c, level, skill) for c in land["cuoi_thua"]]))
            except (QuestionRuleError, ValueError) as error:
                print(f"✗ Thửa “{land['ten']}” có câu không hợp lệ: {getattr(error, 'message', error)}. Chưa nạp gì.")
                return 1
            todo.append((land, lessons))
        db.rollback()

        for land, lessons in todo:
            land_id = path_service.create_land(db, SimpleNamespace(cap_do_id=level, ky_nang=skill, ten=land["ten"],
                                                                   muc_tieu=land["muc_tieu"]), uid)
            for pos, (name, questions) in enumerate(lessons, start=1):
                qids = []
                for question in questions:
                    qid = create_question(db, question, uid)
                    publish_question(db, qid)
                    qids.append(qid)
                lesson_id = path_service.create_lesson(db, SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=name,
                                                                           muc_tieu=None, tai_lieu_id=None), uid)
                path_service.set_lesson_items(db, lesson_id, [SimpleNamespace(cau_hoi_id=q) for q in qids])
                path_service.lesson_status(db, lesson_id, "dang")
            path_service.land_status(db, land_id, "dang")
            print(f"→ {label} · {land['ten']}: 20 câu bài + 10 câu cuối thửa, đã đăng")
        print("Xong.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
