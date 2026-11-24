"""Mở rộng Lộ trình Ôn luyện Thửa 2 cho Nghe (HSK 1–4) và Viết (HSK 4).

- Bổ sung Thửa 2 (4 bài × 5 câu + 1 Kiểm tra cuối thửa × 10 câu = 30 lượt câu/thửa, trong đó 25 câu biên soạn mới tinh)
  cho Nghe HSK 1, Nghe HSK 2, Nghe HSK 3, Nghe HSK 4 và Viết HSK 4.
- Tổng hợp song song 100 tệp âm thanh đối thoại đa giọng đọc (男 / 女 / 问) chuẩn phổ thông cho Nghe HSK 1–4.
- Tự động gắn `tai_lieu_id` tương ứng (theo cấp + kỹ năng) cho các bài mới.
- Đưa toàn bộ 16/16 ô (cấp × kỹ năng) đạt ≥ 2 thửa đã đăng, mở khóa tính năng "Vượt đến thửa" trên mọi kỹ năng.
- An toàn khi chạy lại nhiều lần (idempotent).
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.exam_authoring.services.ai_media_service import make_audio
from app.modules.practice_authoring.services import path_service
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

DATA_DIR = Path(__file__).resolve().parent / "data"


def place(options: list[str], correct_index: int, slot: int) -> tuple[list[str], int]:
    right = options[correct_index]
    others = [o for i, o in enumerate(options) if i != correct_index]
    idx = slot % len(options)
    others.insert(idx, right)
    return others, idx


def mc(opts: list[str], answer: int) -> list[dict]:
    return [{"noi_dung": o, "la_dap_an_dung": i == answer} for i, o in enumerate(opts)]


def land_exists(db, level_id: int, skill: str, name: str) -> bool:
    return bool(
        db.execute(
            text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = :k AND ten = :t LIMIT 1"),
            {"c": level_id, "k": skill, "t": name},
        ).first()
    )


def seed_listening_lands(db, uid: int, levels: dict[str, int], nhom_map: dict[str, int]) -> tuple[int, int]:
    listen_file = DATA_DIR / "lo_trinh_nghe_thua2_hsk1234.json"
    data = json.loads(listen_file.read_text(encoding="utf-8"))
    pending_lands = []
    audio_jobs = []

    for land in data["lands"]:
        cap = int(land["cap"])
        level_id = levels[f"HSK{cap}"]
        if land_exists(db, level_id, "nghe", land["ten"]):
            print(f"· Bỏ qua Nghe HSK {cap} · {land['ten']} (đã tồn tại)")
            continue
        assert len(land["bai"]) == 4, f"Nghe HSK {cap} phải có đúng 4 bài"
        for b in land["bai"]:
            assert len(b["items"]) == 5, f"Bài {b['ten']} phải có 5 câu"
            for it in b["items"]:
                audio_jobs.append((cap, it))
        assert len(land["cuoi_thua_moi"]) == 5, f"Nghe HSK {cap} cuối thửa mới phải có 5 câu"
        for it in land["cuoi_thua_moi"]:
            audio_jobs.append((cap, it))
        pending_lands.append((cap, level_id, land))

    if not pending_lands:
        return 0, 0

    print(f"Đang tổng hợp song song {len(audio_jobs)} tệp âm thanh đối thoại đa giọng cho Nghe HSK 1–4...")

    def synth(job):
        cap, item = job
        plays = 2 if cap <= 3 else 1
        slow = cap <= 2
        item["tep_audio"] = make_audio(item["loi_nghe"], plays=plays, slow=slow)
        return item["tep_audio"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(synth, audio_jobs))

    slot_counter = 0
    lands_added, qs_added = 0, 0

    for cap, level_id, land in pending_lands:
        def save_q(spec: dict) -> int:
            nonlocal slot_counter, qs_added
            opts, ans = place(spec["raw_opts"], 0, slot_counter)
            slot_counter += 1
            qid = create_question(
                db,
                QuestionIn(
                    dang="chon_mot",
                    cap_do_id=level_id,
                    ky_nang="nghe",
                    dung_on_luyen=True,
                    dung_thi_thu=False,
                    nguon_noi_dung="tu_soan",
                    nhom_kien_thuc_id=nhom_map[spec["nhom"]],
                    tep_audio=spec["tep_audio"],
                    noi_dung=spec["noi_dung"],
                    pinyin=spec.get("pinyin"),
                    loi_nghe=spec["loi_nghe"],
                    dich_nghia=spec["dich_nghia"],
                    goi_y=spec["goi_y"],
                    goi_y_2=spec["goi_y_2"],
                    giai_thich=spec["giai_thich"],
                    phuong_an=mc(opts, ans),
                ),
                uid,
            )
            publish_question(db, qid, uid)
            qs_added += 1
            return qid

        lesson_rows = []
        all_lesson_qids = []
        for b in land["bai"]:
            qids = [save_q(it) for it in b["items"]]
            lesson_rows.append((b["ten"], qids))
            all_lesson_qids.extend(qids)

        new_final_qids = [save_q(it) for it in land["cuoi_thua_moi"]]
        review_picks = [all_lesson_qids[idx] for idx in (0, 4, 8, 12, 16)]
        final_10 = new_final_qids + review_picks

        land_id = path_service.create_land(
            db,
            SimpleNamespace(cap_do_id=level_id, ky_nang="nghe", ten=land["ten"], muc_tieu=land["muc_tieu"]),
            uid,
        )
        for pos, (lname, qids) in enumerate(lesson_rows + [("Kiểm tra cuối thửa", final_10)], start=1):
            lid = path_service.create_lesson(
                db,
                SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=lname, muc_tieu=None, tai_lieu_id=None),
                uid,
            )
            path_service.set_lesson_items(db, lid, [SimpleNamespace(cau_hoi_id=q) for q in qids])
            path_service.lesson_status(db, lid, "dang")
        path_service.land_status(db, land_id, "dang")
        lands_added += 1
        print(f"→ Đã đăng Nghe HSK {cap} · Thửa 2: {land['ten']} (4 bài + 1 cuối thửa = 30 lượt câu)")

    return lands_added, qs_added


def seed_writing_hsk4_land2(db, uid: int, level_id: int, nhom_map: dict[str, int]) -> tuple[int, int]:
    write_file = DATA_DIR / "lo_trinh_viet_thua2_hsk4.json"
    land = json.loads(write_file.read_text(encoding="utf-8"))
    existing_land = db.execute(
        text("SELECT id, ma_goc_id, trang_thai FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'viet' AND ten = :t ORDER BY id DESC LIMIT 1"),
        {"c": level_id, "t": land["ten"]},
    ).mappings().first()
    if existing_land and existing_land["trang_thai"] == "da_dang":
        print(f"· Bỏ qua Viết HSK 4 · {land['ten']} (đã đăng)")
        return 0, 0

    qs_added = 0

    def save_write_q(spec: dict) -> int:
        nonlocal qs_added
        existing_q = db.execute(
            text("SELECT id FROM cau_hoi WHERE cap_do_id = :c AND ky_nang = 'viet' AND dang = :d AND noi_dung = :n AND dich_nghia = :dn AND trang_thai = 'da_dang' LIMIT 1"),
            {"c": level_id, "d": spec["dang"], "n": spec["noi_dung"], "dn": spec["dich_nghia"]},
        ).scalar_one_or_none()
        if existing_q is not None:
            return int(existing_q)
        dang = spec["dang"]
        kwargs = dict(
            dang=dang,
            cap_do_id=level_id,
            ky_nang="viet",
            dung_on_luyen=True,
            dung_thi_thu=False,
            nguon_noi_dung="tu_soan",
            nhom_kien_thuc_id=nhom_map[spec["nhom"]],
            noi_dung=spec["noi_dung"],
            dich_nghia=spec["dich_nghia"],
            goi_y=spec["goi_y"],
            goi_y_2=spec["goi_y_2"],
            giai_thich=spec["giai_thich"],
        )
        if dang == "sap_xep":
            joined = "".join(p.strip() for p in spec["manh_ghep"])
            accepted = list(spec["dap_an_chap_nhan"])
            if joined not in accepted:
                accepted.insert(0, joined)
            kwargs["phuong_an"] = [{"noi_dung": p, "la_dap_an_dung": False} for p in spec["manh_ghep"]]
            kwargs["dap_an_chap_nhan"] = accepted
        elif dang == "dich_cau":
            kwargs["dap_an_chap_nhan"] = list(spec["dap_an_chap_nhan"])
            kwargs["diem_toi_da"] = Decimal("10.00")
            kwargs["nguong_dat"] = Decimal("6.00")
            kwargs["tieu_chi_mo_ta"] = spec["tieu_chi_mo_ta"]
        elif dang == "viet_mo":
            kwargs["tu_bat_buoc"] = spec["tu_bat_buoc"]
            kwargs["diem_toi_da"] = Decimal("10.00")
            kwargs["nguong_dat"] = Decimal("6.00")
            kwargs["tieu_chi_mo_ta"] = spec["tieu_chi_mo_ta"]
        else:
            raise ValueError(f"Dạng câu viết không hợp lệ: {dang}")

        qid = create_question(db, QuestionIn(**kwargs), uid)
        publish_question(db, qid, uid)
        qs_added += 1
        return qid

    lesson_rows = []
    all_lesson_qids = []
    for b in land["bai"]:
        assert len(b["items"]) == 5, f"Bài viết {b['ten']} phải có 5 câu"
        qids = [save_write_q(it) for it in b["items"]]
        lesson_rows.append((b["ten"], qids))
        all_lesson_qids.extend(qids)

    assert len(land["cuoi_thua_moi"]) == 5, "Viết HSK 4 cuối thửa mới phải có 5 câu"
    new_final_qids = [save_write_q(it) for it in land["cuoi_thua_moi"]]
    review_picks = [all_lesson_qids[idx] for idx in (0, 4, 8, 11, 15)]
    final_10 = new_final_qids + review_picks

    if existing_land:
        land_id = int(existing_land["id"])
        land_root = int(existing_land["ma_goc_id"])
    else:
        land_id = path_service.create_land(
            db,
            SimpleNamespace(cap_do_id=level_id, ky_nang="viet", ten=land["ten"], muc_tieu=land["muc_tieu"]),
            uid,
        )
        land_root = land_id

    for pos, (lname, qids) in enumerate(lesson_rows + [(f"Kiểm tra cuối thửa: {land['ten']}", final_10)], start=1):
        existing_slot = db.execute(
            text("SELECT id, trang_thai FROM bo_de WHERE thua_id = :g AND vi_tri = :v ORDER BY id DESC LIMIT 1"),
            {"g": land_root, "v": pos},
        ).mappings().first()
        if existing_slot and existing_slot["trang_thai"] == "da_dang":
            continue
        lid = (
            int(existing_slot["id"])
            if existing_slot
            else path_service.create_lesson(
                db,
                SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=lname, muc_tieu=None, tai_lieu_id=None),
                uid,
            )
        )
        path_service.set_lesson_items(db, lid, [SimpleNamespace(cau_hoi_id=q) for q in qids])
        path_service.lesson_status(db, lid, "dang")
    path_service.land_status(db, land_id, "dang")
    print(f"→ Đã đăng Viết HSK 4 · Thửa 2: {land['ten']} (4 bài + 1 cuối thửa = 30 lượt câu)")
    return 1, qs_added


def main() -> int:
    db = SessionLocal()
    try:
        uid = db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one()
        levels = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}
        nhom_map = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM nhom_kien_thuc")).all()}

        l1, q1 = seed_listening_lands(db, uid, levels, nhom_map)
        l2, q2 = seed_writing_hsk4_land2(db, uid, levels["HSK4"], nhom_map)

        # Liên kết tai_lieu_id tương ứng (cùng cấp + kỹ năng) cho các bài ôn luyện mới
        linked = db.execute(text("""
            UPDATE bo_de b
            JOIN bo_de thua ON thua.ma_goc_id = b.thua_id AND thua.loai = 'thua'
            JOIN (
                SELECT cap_do_id, ky_nang, MAX(id) AS tl_id
                FROM tai_lieu
                WHERE trang_thai = 'da_dang' AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL
                GROUP BY cap_do_id, ky_nang
            ) tl ON tl.cap_do_id = thua.cap_do_id AND tl.ky_nang = thua.ky_nang
            SET b.tai_lieu_id = tl.tl_id
            WHERE b.loai IN ('bai', 'cuoi_thua') AND b.tai_lieu_id IS NULL
        """)).rowcount
        db.commit()
        print(f"HOÀN TẤT LỘ TRÌNH BỔ SUNG: +{l1 + l2} thửa mới, +{q1 + q2} câu hỏi mới, gắn học liệu cho {linked} bài.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
