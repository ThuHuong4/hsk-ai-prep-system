"""Nạp bộ luyện Nghe HSK 2, 3, 4 (45 câu) vào Ôn luyện từ scripts/data/nghe_hsk234.json.

Nguồn: học liệu Xianglingo soạn mới có hỗ trợ ChatGPT (20/11/2026); đề mẫu chinesetest.cn chỉ tham khảo dạng bài.
Cần Giảng viên tiếng Trung rà soát từ vựng, độ khó và âm thanh trước khi dùng chính thức.

Cách chạy (trong thư mục backend):  python scripts/seed_nghe_hsk234.py <email Giảng viên>

Ánh xạ vào lộ trình hiện hành (mục 4.1):
- Mỗi cấp một thửa Nghe; 3 "thửa" trong bộ câu thành Bài 1–3 của thửa đó (mỗi bài 5 câu).
  Lý do: thửa chưa có Kiểm tra cuối thửa thì không thu hoạch được, nên thửa thứ 2, 3 sẽ bị khóa mãi.
- Không tạo Bài 4 và Kiểm tra cuối thửa (bộ này không có câu cho phần đó): hai ô hiện "Sắp có".
- Mã H2_NGHE_T01_C01… chỉ dùng để đặt tên tệp âm thanh, không phải id trong CSDL.
- Câu chỉ dùng cho Ôn luyện. Học viên thấy câu hỏi và phương án tiếng Trung (HSK 2 có pinyin ở phương án);
  lời thoại, đáp án, nghĩa tiếng Việt, giải thích chỉ trả về sau khi kiểm tra (máy chủ đã xử lý).
- Âm thanh: backend/uploads/practice/hsk234_nghe/<mã câu>.mp3; thiếu tệp nào thì dừng, không nạp gì.
- Thửa cùng tên đã có ở cấp đó (Nghe) thì bỏ qua, không nạp trùng.
"""
import json
import re
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

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "scripts" / "data" / "nghe_hsk234.json"
AUDIO_DIR = "practice/hsk234_nghe"
LANDS = {
    2: ("Hội thoại hằng ngày", "Nghe giờ giấc, mua sắm, đi lại và nhận ra thông tin đã thay đổi trong hội thoại ngắn"),
    3: ("Học tập, sức khỏe và du lịch", "Nghe nguyên nhân, trình tự, lời khuyên và thay đổi kế hoạch trong hội thoại"),
    4: ("Công việc, lựa chọn và quan điểm", "Suy luận mục đích, quyết định cuối cùng và thông điệp chính của hội thoại, đoạn văn"),
}
OPTIONS = {2: 3, 3: 3, 4: 4}


def dialogue_lines(text_: str) -> str:
    """'女：…男：…' → mỗi lượt một dòng; đoạn độc thoại giữ nguyên."""
    parts = re.split(r"(女|男)：", text_)
    if len(parts) == 1:
        return text_.strip()
    return "\n".join(f"{parts[i]}：{parts[i + 1].strip()}" for i in range(1, len(parts), 2))


def payload(q: dict, level_id: int, cap: int) -> QuestionIn:
    if len(q["phuong_an"]) != OPTIONS[cap]:
        raise QuestionRuleError(f"{q['ma_cau']}: HSK {cap} cần {OPTIONS[cap]} phương án")
    if sum(o["ky_hieu"] == q["dap_an_dung"] for o in q["phuong_an"]) != 1:
        raise QuestionRuleError(f"{q['ma_cau']}: đáp án đúng không khớp phương án")
    options = [{"noi_dung": f"{o['noi_dung_zh']} [{o['pinyin']}]" if cap == 2 and o.get("pinyin") else o["noi_dung_zh"],
                "la_dap_an_dung": o["ky_hieu"] == q["dap_an_dung"]} for o in q["phuong_an"]]
    meaning = "\n".join(f"{o['ky_hieu']}. {o['noi_dung_zh']} – {o['nghia_vi']}" for o in q["phuong_an"] if o.get("nghia_vi"))
    body = QuestionIn(
        dang="chon_mot", cap_do_id=level_id, ky_nang="nghe", dung_on_luyen=True, dung_thi_thu=False,
        tep_audio=f"{AUDIO_DIR}/{q['ma_cau']}.mp3", noi_dung=q["cau_hoi_zh"],
        loi_nghe=f"{dialogue_lines(q['loi_thoai'])}\n问：{q['cau_hoi_zh']}",
        dich_nghia=f"{q['cau_hoi_vi']}\n{meaning}".strip(), giai_thich=q["giai_thich_vi"], phuong_an=options,
    )
    validate_question(body)
    return body


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/seed_nghe_hsk234.py <email Giảng viên>")
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    questions = [q for t in data["thua"] for b in t["bai_luyen"] for q in b["cau_hoi"]]
    missing = [q["ma_cau"] for q in questions if not (BACKEND / "uploads" / AUDIO_DIR / f"{q['ma_cau']}.mp3").is_file()]
    if missing:
        print(f"✗ Thiếu {len(missing)}/{len(questions)} tệp âm thanh trong uploads/{AUDIO_DIR}, chưa nạp gì. Ví dụ: {missing[0]}.mp3")
        return 1
    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[1].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        levels = {m: i for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}
        plan = []
        for cap in (2, 3, 4):
            level_id = levels.get(f"HSK{cap}")
            if level_id is None:
                print(f"✗ Chưa có cấp HSK{cap} trong bảng cap_do")
                return 1
            name, goal = LANDS[cap]
            if db.execute(text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'nghe' AND ten = :t LIMIT 1"),
                          {"c": level_id, "t": name}).first():
                print(f"· Bỏ qua Nghe HSK {cap} · {name} (đã có)")
                continue
            groups = sorted((t for t in data["thua"] if t["cap_hsk"] == cap), key=lambda t: t["thu_tu"])
            try:
                lessons = [(g["ten_thua"], [payload(q, level_id, cap) for b in g["bai_luyen"] for q in sorted(b["cau_hoi"], key=lambda x: x["thu_tu"])])
                           for g in groups]
            except (QuestionRuleError, ValueError) as error:
                print(f"✗ HSK {cap}: {getattr(error, 'message', error)}. Chưa nạp gì.")
                return 1
            if len(lessons) > 4 or any(len(qs) != 5 for _, qs in lessons):
                print(f"✗ HSK {cap}: mỗi bài phải đúng 5 câu và tối đa 4 bài. Chưa nạp gì.")
                return 1
            plan.append((cap, level_id, name, goal, lessons))
        db.rollback()

        for cap, level_id, name, goal, lessons in plan:
            land_id = path_service.create_land(db, SimpleNamespace(cap_do_id=level_id, ky_nang="nghe", ten=name, muc_tieu=goal), uid)
            for pos, (lesson_name, items) in enumerate(lessons, start=1):
                qids = []
                for item in items:
                    qid = create_question(db, item, uid)
                    publish_question(db, qid)
                    qids.append(qid)
                lesson_id = path_service.create_lesson(db, SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=lesson_name,
                                                                           muc_tieu=None, tai_lieu_id=None), uid)
                path_service.set_lesson_items(db, lesson_id, [SimpleNamespace(cau_hoi_id=q) for q in qids])
                path_service.lesson_status(db, lesson_id, "dang")
            path_service.land_status(db, land_id, "dang")
            print(f"→ Nghe HSK {cap} · {name}: {len(lessons)} bài × 5 câu, đã đăng (Bài 4 và Kiểm tra cuối thửa: Sắp có)")
        print("Xong.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
