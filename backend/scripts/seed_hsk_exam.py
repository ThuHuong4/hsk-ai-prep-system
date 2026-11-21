"""Nạp một đề thi thử HSK từ tệp dữ liệu JSON (scripts/data/*.json) vào CSDL Xianglingo.

Dữ liệu lấy từ đề, lời nghe và đáp án do chủ dự án cung cấp:
    hsk2_h20901.json – HSK 2 – Đề 1 (H20901)
    hsk3_h31001.json – HSK 3 – Đề 1 (H31001)
    hsk4_h41001.json – HSK 4 – Đề 1 (H41001)
Hình và âm thanh nằm sẵn trong uploads/exams/<mã>/.

Cách chạy (đứng trong thư mục backend):
    python scripts/seed_hsk_exam.py scripts/data/hsk2_h20901.json gv.test@gmail.com
(email là tài khoản Giảng viên đứng tên người tạo). Đề đã có mã đề này thì dừng, không tạo trùng.
Toàn bộ dữ liệu và tệp hình/âm thanh được kiểm tra trước khi ghi CSDL.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemIn  # noqa: E402
from app.modules.exam_authoring.services import exam_service  # noqa: E402
from app.modules.questions.schemas.question_payload import QuestionIn  # noqa: E402
from app.modules.questions.services.question_rules import validate_question  # noqa: E402
from app.modules.questions.services.question_status import publish_question  # noqa: E402
from app.modules.questions.services.save_question import create_question  # noqa: E402

UPLOADS = Path(__file__).resolve().parents[1] / "uploads"


def payloads(plan: list[dict], level: int) -> list[tuple[int, QuestionIn, list[bool] | bool]]:
    """Dựng và kiểm tra trước toàn bộ câu; lỗi dữ liệu thì dừng trước khi ghi CSDL."""
    out = []
    for index, entry in enumerate(plan, start=1):
        if "group" in entry:
            body = {**entry["group"], "cap_do_id": level, "cau_con": [c for c, _ in entry["children"]]}
            flags = [bool(ex) for _, ex in entry["children"]]
        else:
            body = {**entry["q"], "cap_do_id": level}
            flags = bool(entry.get("ex"))
        try:
            question = QuestionIn(**body)
            validate_question(question)
        except Exception as error:  # báo đúng mục lỗi để sửa tệp dữ liệu
            raise SystemExit(f"✗ Mục {index} (phần {entry['part']}) không hợp lệ: {error}")
        out.append((entry["part"], question, flags))
    return out


def check_media(data: dict) -> None:
    paths = [data["exam"]["audio"]]
    for entry in data["plan"]:
        items = [entry.get("q") or entry.get("group")] + [c for c, _ in entry.get("children", [])]
        for item in items:
            paths += [item.get("tep_hinh")] + [o.get("tep_hinh") for o in item.get("phuong_an", [])]
    missing = sorted({p for p in paths if p and not (UPLOADS / p).is_file()})
    if missing:
        raise SystemExit("✗ Thiếu tệp trong uploads/: " + ", ".join(missing[:5]) + (" …" if len(missing) > 5 else ""))


def main() -> int:
    if len(sys.argv) != 3:
        print("Cách dùng: python scripts/seed_hsk_exam.py <tệp JSON> <email Giảng viên>")
        return 1
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    exam = data["exam"]
    check_media(data)
    db = SessionLocal()
    try:
        lecturer = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                              {"e": sys.argv[2].strip().lower()}).scalar_one_or_none()
        if lecturer is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        level = db.execute(text("SELECT id FROM cap_do WHERE ma = :m"), {"m": exam["level"]}).scalar_one_or_none()
        if level is None:
            print(f"✗ Chưa có cấp {exam['level']} trong bảng cap_do")
            return 1
        if db.execute(text("SELECT 1 FROM bo_de WHERE ma_de = :m"), {"m": exam["code"]}).first():
            print(f"✗ Đề {exam['code']} đã có, không nạp lại")
            return 1
        db.rollback()

        prepared = payloads(data["plan"], level)
        items: list[ExamItemIn] = []
        for part, question, flags in prepared:
            qid = create_question(db, question, lecturer)
            publish_question(db, qid)
            if isinstance(flags, list):
                child_ids = [r[0] for r in db.execute(
                    text("SELECT id FROM cau_hoi WHERE cau_cha_id = :p ORDER BY id"), {"p": qid}).all()]
                items += [ExamItemIn(cau_hoi_id=c, phan=part, la_cau_vi_du=ex) for c, ex in zip(child_ids, flags)]
            else:
                items.append(ExamItemIn(cau_hoi_id=qid, phan=part, la_cau_vi_du=flags))

        exam_id = exam_service.create_exam(db, ExamInfoIn(
            cap_do_id=level, ten=exam["ten"], ma_de=exam["code"], thoi_luong_phut=exam["phut"],
            nguon=exam["nguon"], tep_audio_chung=exam["audio"],
        ), lecturer)
        exam_service.set_exam_items(db, exam_id, items)
        exam_service.publish_exam(db, exam_id)
        scored = sum(1 for i in items if not i.la_cau_vi_du)
        print(f"→ Đã nạp {exam['ten']} ({exam['code']}): {scored} câu tính điểm, {len(items) - scored} câu ví dụ. Đề đã đăng.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
