"""Nạp thửa Ôn luyện Nghe HSK 1 "Hội thoại ngắn hằng ngày" (30 câu) từ scripts/data/hsk1_nghe_on_luyen.json.

Nguồn câu hỏi: Xianglingo — học liệu soạn mới có hỗ trợ ChatGPT — 19/11/2026 (không phải đề thi chính thức).
Gồm 4 bài × 5 câu và Kiểm tra cuối thửa 10 câu; câu chỉ dùng cho Ôn luyện.

Âm thanh: mỗi câu một tệp, đặt tại backend/uploads/practice/hsk1_nghe/H1_N001.mp3 … H1_N030.mp3
(hoặc .wav cùng tên, ví dụ tệp do scripts/tao_am_thanh_hsk1_nghe_windows.py tạo).
Thiếu bất kỳ tệp nào thì script dừng, không tạo câu hay thửa nào (không gắn âm thanh giả).

Cách chạy (đứng trong thư mục backend):
    python scripts/seed_hsk1_nghe.py gv.test@gmail.com
Thửa cùng tên đã có ở HSK 1 – Nghe thì bỏ qua, không nạp trùng.
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
from app.modules.questions.services.question_rules import validate_question  # noqa: E402
from app.modules.questions.services.question_status import publish_question  # noqa: E402
from app.modules.questions.services.save_question import create_question  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "scripts" / "data" / "hsk1_nghe_on_luyen.json"


def audio_path(item: dict) -> str | None:
    """Đường dẫn tệp âm thanh đang có: ưu tiên .mp3, sau đó .wav cùng tên."""
    for ext in (".mp3", ".wav"):
        rel = str(Path(item["tep_audio"]).with_suffix(ext)).replace("\\", "/")
        if (BACKEND / "uploads" / rel).is_file():
            return rel
    return None


def payload(item: dict, level: int) -> QuestionIn:
    body = {
        "dang": "chon_mot", "cap_do_id": level, "ky_nang": "nghe", "dung_on_luyen": True, "dung_thi_thu": False,
        "tep_audio": audio_path(item), "noi_dung": item["noi_dung"], "loi_nghe": item["loi_nghe"],
        "giai_thich": item["giai_thich"], "phuong_an": item["phuong_an"],
    }
    question = QuestionIn(**body)
    validate_question(question)
    return question


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/seed_hsk1_nghe.py <email Giảng viên>")
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    all_items = [c for lesson in data["bai"] for c in lesson["cau"]] + data["cuoi_thua"]
    missing = [c["tep_audio"] for c in all_items if audio_path(c) is None]
    if missing:
        print(f"✗ Thiếu {len(missing)}/{len(all_items)} tệp âm thanh, chưa nạp gì. Ví dụ: uploads/{missing[0]}")
        return 1

    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[1].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        level = db.execute(text("SELECT id FROM cap_do WHERE ma = :m"), {"m": data["thua"]["cap"]}).scalar_one_or_none()
        if level is None:
            print("✗ Chưa có cấp HSK1 trong bảng cap_do")
            return 1
        land = data["thua"]
        if db.execute(text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'nghe' AND ten = :t LIMIT 1"),
                      {"c": level, "t": land["ten"]}).first():
            print(f"· Bỏ qua: thửa Nghe “{land['ten']}” đã có")
            return 0
        db.rollback()

        prepared = [(lesson["ten"], [payload(c, level) for c in lesson["cau"]]) for lesson in data["bai"]]
        prepared.append(("Kiểm tra cuối thửa", [payload(c, level) for c in data["cuoi_thua"]]))

        land_id = path_service.create_land(db, SimpleNamespace(cap_do_id=level, ky_nang="nghe", ten=land["ten"],
                                                               muc_tieu=land["muc_tieu"]), uid)
        for pos, (name, questions) in enumerate(prepared, start=1):
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
        print(f"→ Nghe HSK 1 · {land['ten']}: 4 bài × 5 câu + 10 câu cuối thửa, đã đăng")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
