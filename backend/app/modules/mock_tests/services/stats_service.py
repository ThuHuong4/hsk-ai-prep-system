"""Thống kê Thi thử của Học viên (mục 6.2).

- Chỉ tính lượt đã nộp và chấm xong hết; lượt còn câu chờ chấm/lỗi chấm đếm riêng, không tính vào điểm.
- Tách theo cấp (không trộn thang 200 với 300). Tính lại mỗi lần mở trang nên sửa điểm thì thống kê cập nhật theo.
- Mỗi cấp: số lượt, điểm gần nhất/cao nhất/trung bình, số lượt đạt, điểm từng lượt (biểu đồ, có mốc đạt),
  điểm theo kỹ năng (lượt đầu → lượt gần nhất), dạng câu cộng dồn mọi lượt xếp từ yếu lên.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.mock_tests.services.attempt_service import _answers, score_attempt
from app.modules.mock_tests.services.content import load_items
from app.modules.mock_tests.services.roadmap_service import DANG_VI, SKILL_VI, WEAK_BELOW, group_scores

MAX_ATTEMPTS = 60  # lượt gần nhất được tính (đủ cho biểu đồ, tránh trang chậm)


def student_stats(db: Session, uid: int) -> dict:
    rows = db.execute(
        text("""SELECT l.id, l.bo_de_id, l.nguoi_dung_id, l.nop_luc, b.ten AS ten_de, b.ma_goc_id,
                       cd.id AS cap_do_id, cd.ma AS cap_ma, cd.ten AS cap_ten, cd.thu_tu AS cap_thu_tu
                FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id JOIN cap_do cd ON cd.id = b.cap_do_id
                WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND l.trang_thai = 'da_nop'
                ORDER BY l.nop_luc DESC, l.id DESC LIMIT :n"""),
        {"u": uid, "n": MAX_ATTEMPTS},
    ).mappings().all()
    levels: dict[int, dict] = {}
    pending = 0
    latest = None  # cấp của lượt chấm xong gần nhất: mở trang thì chọn sẵn cấp này
    for r in reversed(rows):  # cũ → mới
        attempt = dict(r)
        items, questions, _ = load_items(db, attempt["bo_de_id"])
        score = score_attempt(db, attempt, items, questions, _answers(db, attempt["id"]))
        if score["so_cau_cho_cham"]:
            pending += 1
            continue
        lv = levels.setdefault(attempt["cap_do_id"], {
            "cap_do_id": attempt["cap_do_id"], "cap": attempt["cap_ten"], "thu_tu": attempt["cap_thu_tu"],
            "diem_toi_da": score["diem_toi_da"], "diem_dat": score["diem_dat"], "luot": [], "_groups": {}, "_skills": [],
        })
        latest = attempt["cap_do_id"]
        lv["luot"].append({"id": attempt["id"], "ten_de": attempt["ten_de"], "nop_luc": attempt["nop_luc"],
                           "tong_diem": score["tong_diem"], "dat": score["dat"]})
        lv["_skills"].append({s["ky_nang"]: s["diem"] for s in score["ky_nang"]})
        groups, _ = group_scores(db, attempt, attempt["cap_ma"])
        for g in groups:
            agg = lv["_groups"].setdefault((g["ky_nang"], g["dang"]), {
                "ky_nang": g["ky_nang"], "dang": g["dang"], "ten": f"{SKILL_VI.get(g['ky_nang'], g['ky_nang'])} · {DANG_VI.get(g['dang'], g['dang'])}", "tong": 0, "dung": 0.0, "phan_ten": []})
            agg["tong"] += g["tong"]
            agg["dung"] += g["dung"]
            agg["phan_ten"] = sorted(set(agg["phan_ten"]) | set(g["phan_ten"]))
    db.rollback()

    out = []
    for lv in sorted(levels.values(), key=lambda x: x["thu_tu"]):
        scores = [a["tong_diem"] for a in lv["luot"]]
        skills = []
        for name in ("nghe", "doc", "viet"):
            seq = [s[name] for s in lv["_skills"] if name in s]
            if seq:
                skills.append({"ky_nang": name, "dau": seq[0], "gan_nhat": seq[-1],
                               "trung_binh": round(sum(seq) / len(seq), 2), "so_luot": len(seq)})
        groups = []
        for g in lv["_groups"].values():
            g["ty_le"] = round(g["dung"] / g["tong"], 3) if g["tong"] else 0.0
            g["dung"] = round(g["dung"], 2)
            g["yeu"] = g["ty_le"] < WEAK_BELOW
            groups.append(g)
        groups.sort(key=lambda g: (g["ty_le"], -g["tong"]))
        out.append({
            "cap_do_id": lv["cap_do_id"], "cap": lv["cap"], "diem_toi_da": lv["diem_toi_da"], "diem_dat": lv["diem_dat"],
            "so_luot": len(scores), "so_luot_dat": sum(1 for a in lv["luot"] if a["dat"]),
            "diem_gan_nhat": scores[-1], "diem_cao_nhat": max(scores), "diem_trung_binh": round(sum(scores) / len(scores), 2),
            "luot": lv["luot"], "ky_nang": skills, "dang_cau": groups,
        })
    return {"cap": out, "cap_gan_nhat": latest, "so_luot_cho_cham": pending}
