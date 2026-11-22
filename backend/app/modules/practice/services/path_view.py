"""Bản đồ Ôn luyện của Học viên (mục 4.1): Kỹ năng → Cấp → Thửa → 5 ô.
    
- Chỉ hiện thửa/bài đang đăng. Thửa chưa có bài đăng → "Chưa xuất bản", không tạo tiến độ giả.
- Mở khóa: thửa đầu mở; thửa sau mở khi kiểm tra cuối thửa trước đạt. Trong thửa, ô sau mở khi ô trước đạt.
- Đạt = lượt đã nộp có mọi câu đúng (5/5, 10/10). Tiến độ tính theo bài gốc (mọi phiên bản).
- Vượt đến thửa: đạt kiểm tra vượt tới thửa T → các thửa trước T hiện "Đã vượt" (quyền bỏ qua, không phải đã học), T mở.
- Cấp mở sẵn: Nghe, Đọc, Từ vựng mở cấp đầu; Viết mở cấp thứ 3 (HSK 3). Cấp khác mở khi đạt
  "Bắt đầu cấp L" (mở L) hoặc "Vượt chặng L" (mở L+1), riêng từng kỹ năng (mục 4.2).
"""
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

SKILLS = ("nghe", "doc", "tu_vung", "viet")
START_ORDER = {"nghe": 1, "doc": 1, "tu_vung": 1, "viet": 3}
LESSON_SIZE = {"bai": 5, "cuoi_thua": 10}


def levels(db: Session) -> list[dict]:
    rows = db.execute(text("SELECT id, ma, ten, thu_tu FROM cap_do WHERE trang_thai = 'da_dang' ORDER BY thu_tu")).mappings().all()
    return [dict(r) for r in rows]


def level_open(level: dict, skill: str, opened: set[int] | None = None) -> bool:
    """opened: id các cấp Học viên đã mở bằng kiểm tra (opened_levels); None = chỉ cấp mở sẵn (Khách)."""
    return level["thu_tu"] == START_ORDER[skill] or bool(opened and level["id"] in opened)


def level_tests(db: Session, uid: int, skill: str) -> dict:
    """Lượt Bắt đầu cấp / Vượt chặng đã đạt của Học viên ở một kỹ năng: {'bat_dau_cap': {cap_id}, 'vuot_chang': {cap_id}}."""
    out = {"bat_dau_cap": set(), "vuot_chang": set()}
    if not uid:
        return out
    for kind, cap in db.execute(
        text("""SELECT DISTINCT loai_boc_cau, cap_do_id FROM luot_lam
                WHERE nguoi_dung_id = :u AND ky_nang = :k AND loai_boc_cau IN ('bat_dau_cap', 'vuot_chang')
                  AND trang_thai = 'da_nop' AND ap_dung_luc IS NOT NULL"""),
        {"u": uid, "k": skill},
    ).all():
        out[kind].add(int(cap))
    return out


def opened_levels(db: Session, uid: int, skill: str, lv: list[dict] | None = None) -> set[int]:
    """Id các cấp đã mở nhờ kiểm tra: đạt Bắt đầu cấp L → mở L; đạt Vượt chặng L → mở cấp kế L."""
    lv = lv if lv is not None else levels(db)
    passed = level_tests(db, uid, skill)
    opened = set(passed["bat_dau_cap"])
    for i, level in enumerate(lv):
        if level["id"] in passed["vuot_chang"] and i + 1 < len(lv):
            opened.add(lv[i + 1]["id"])
    return opened


def lesson_progress(db: Session, uid: int, lesson_roots: list[int]) -> dict[int, dict]:
    """Theo bài gốc: đã đạt chưa, đã có lượt nộp chưa, lượt đang làm (nếu có)."""
    if not lesson_roots:
        return {}
    marks = ", ".join(f":r{i}" for i in range(len(lesson_roots)))
    params = {f"r{i}": v for i, v in enumerate(lesson_roots)}
    params["u"] = uid
    rows = db.execute(
        text(f"""
            SELECT b.ma_goc_id, l.id, l.trang_thai,
                   COUNT(a.id) AS tong,
                   SUM(CASE WHEN v.diem >= 1 THEN 1 ELSE 0 END) AS dung
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            LEFT JOIN cau_tra_loi a ON a.luot_lam_id = l.id
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE l.nguoi_dung_id = :u AND b.ma_goc_id IN ({marks}) AND l.trang_thai IN ('dang_lam', 'da_nop')
            GROUP BY b.ma_goc_id, l.id, l.trang_thai
        """),
        params,
    ).mappings().all()
    out: dict[int, dict] = {}
    for r in rows:
        p = out.setdefault(r["ma_goc_id"], {"dat": False, "da_nop": False, "luot_dang_lam": None})
        if r["trang_thai"] == "dang_lam":
            p["luot_dang_lam"] = r["id"]
        else:
            p["da_nop"] = True
            if r["tong"] and int(r["dung"] or 0) == int(r["tong"]):
                p["dat"] = True
    return out


def skip_targets(db: Session, uid: int) -> set[int]:
    """Thửa gốc mà Học viên đã đạt kiểm tra vượt tới (đã áp dụng quyền)."""
    if not uid:
        return set()
    rows = db.execute(
        text("""SELECT DISTINCT t.ma_goc_id FROM luot_lam l JOIN bo_de t ON t.id = l.thua_dich_id
                WHERE l.nguoi_dung_id = :u AND l.loai_boc_cau = 'vuot_thua' AND l.trang_thai = 'da_nop'
                  AND l.ap_dung_luc IS NOT NULL"""),
        {"u": uid},
    ).all()
    return {int(r[0]) for r in rows}


def land_offset(db: Session, cap_do_id: int, skill: str) -> int:
    """Số thửa đang đăng có bài của cùng kỹ năng ở các cấp thấp hơn → đánh số thửa liên tục qua các cấp."""
    return int(db.execute(
        text("""SELECT COUNT(*) FROM bo_de t JOIN cap_do c ON c.id = t.cap_do_id
                WHERE t.loai = 'thua' AND t.ky_nang = :k AND t.trang_thai = 'da_dang' AND c.trang_thai = 'da_dang'
                  AND c.thu_tu < (SELECT thu_tu FROM cap_do WHERE id = :c)
                  AND EXISTS(SELECT 1 FROM bo_de b WHERE b.thua_id = t.ma_goc_id AND b.loai IN ('bai', 'cuoi_thua')
                             AND b.trang_thai = 'da_dang')"""),
        {"k": skill, "c": cap_do_id},
    ).scalar_one())


def level_passed_over(db: Session, uid: int, cap_do_id: int, skill: str) -> bool:
    """Cấp L được xem là đã vượt hết khi Học viên đạt Bắt đầu cấp ở một cấp cao hơn L,
    hoặc đạt Vượt cấp (vuot_chang) ở chính L hay cấp cao hơn, cùng kỹ năng."""
    if not uid:
        return False
    lv = levels(db)
    order = {l["id"]: l["thu_tu"] for l in lv}
    here = order.get(cap_do_id)
    if here is None:
        return False
    passed = level_tests(db, uid, skill)
    return (any(order.get(c, 0) > here for c in passed["bat_dau_cap"])
            or any(order.get(c, 0) >= here for c in passed["vuot_chang"]))


def build_map(db: Session, uid: int, cap_do_id: int, skill: str) -> list[dict]:
    lands = [dict(r) for r in db.execute(
        text("""SELECT id, ma_goc_id, ten, muc_tieu, vi_tri FROM bo_de
                WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = :k AND trang_thai = 'da_dang'
                ORDER BY vi_tri IS NULL, vi_tri, id"""),
        {"c": cap_do_id, "k": skill},
    ).mappings().all()]
    lessons_by_land: dict[int, list[dict]] = {}
    for land in lands:
        lessons_by_land[land["ma_goc_id"]] = [dict(r) for r in db.execute(
            text("""SELECT b.id, b.ma_goc_id, b.loai, b.vi_tri, b.ten, b.muc_tieu,
                           (SELECT COUNT(*) FROM bo_de_cau_hoi i WHERE i.bo_de_id = b.id) AS so_cau
                    FROM bo_de b WHERE b.thua_id = :t AND b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'da_dang'
                    ORDER BY b.vi_tri"""),
            {"t": land["ma_goc_id"]},
        ).mappings().all()]
    progress = lesson_progress(db, uid, [l["ma_goc_id"] for ls in lessons_by_land.values() for l in ls])
    # Vượt đến thửa (mục 4.2): đạt kiểm tra vượt tới thửa T → mọi thửa trước T là "Đã vượt"
    skipped_to = skip_targets(db, uid)
    roots = [land["ma_goc_id"] for land in lands]
    skip_until = max((roots.index(g) for g in skipped_to if g in roots), default=0)
    if level_passed_over(db, uid, cap_do_id, skill):  # đã vượt lên cấp cao hơn → cả cấp này là "Đã vượt"
        skip_until = len(lands)

    result, open_land = [], True
    number = land_offset(db, cap_do_id, skill)  # số thứ tự thửa liên tục theo kỹ năng (thửa chưa có bài không đánh số)
    for li, land in enumerate(lands):
        lessons = lessons_by_land[land["ma_goc_id"]]
        skipped = li < skip_until
        slots, prev_ok = [], open_land or skipped
        for pos in range(1, 6):
            lesson = next((l for l in lessons if l["vi_tri"] == pos), None)
            if lesson is None:
                slots.append({"vi_tri": pos, "loai": "cuoi_thua" if pos == 5 else "bai", "trang_thai": "chua_xuat_ban"})
                prev_ok = False
                continue
            p = progress.get(lesson["ma_goc_id"], {})
            if p.get("dat"):
                state = "da_xong"
            elif skipped:  # thửa đã vượt: mọi ô chưa xong đều "Đã vượt", kể cả ô đang làm dở (vẫn làm tiếp được)
                state = "da_vuot"
            elif not prev_ok:
                state = "khoa"
            elif p.get("luot_dang_lam"):
                state = "dang_lam"
            elif p.get("da_nop"):
                state = "chua_dat"
            else:
                state = "chua_hoc"
            slots.append({
                "vi_tri": pos, "loai": lesson["loai"], "ma_goc_id": lesson["ma_goc_id"], "ten": lesson["ten"],
                "muc_tieu": lesson["muc_tieu"], "so_cau": LESSON_SIZE[lesson["loai"]], "trang_thai": state,
                "luot_dang_lam": p.get("luot_dang_lam"),
            })
            prev_ok = bool(p.get("dat")) or skipped
        harvested = bool(slots) and slots[4]["trang_thai"] == "da_xong"
        if lessons:
            number += 1
        result.append({
            "ma_goc_id": land["ma_goc_id"], "ten": land["ten"], "muc_tieu": land["muc_tieu"],
            "so_thu_tu": number if lessons else None,
            "mo": open_land or skipped, "co_bai": bool(lessons), "thu_hoach": harvested, "da_vuot": skipped, "o": slots,
        })
        open_land = harvested or li + 1 <= skip_until  # thửa kế là thửa bị vượt hoặc chính thửa đích
    return result


def summarize(lands: list[dict]) -> dict:
    lessons = [o for land in lands for o in land["o"] if o["trang_thai"] != "chua_xuat_ban"]
    nxt = None
    # Bài tiếp theo = ô chưa xong đầu tiên ở thửa đang mở xa nhất (đã vượt tới thửa sau thì Xiang đứng ở thửa sau),
    # không lùi về các ô còn lại của thửa đã vượt.
    for land in reversed(lands):
        if not land["mo"] or land.get("da_vuot"):
            continue
        for o in land["o"]:
            if o["trang_thai"] in ("dang_lam", "chua_dat", "chua_hoc"):
                nxt = {"thua": land["ten"], **{k: o[k] for k in ("ma_goc_id", "ten", "vi_tri", "loai", "trang_thai")}}
                break
        if nxt:
            break
    return {"so_bai": len(lessons), "da_xong": sum(1 for o in lessons if o["trang_thai"] == "da_xong"), "bai_tiep": nxt}


def streak_days(db: Session, uid: int) -> int:
    """Chuỗi ngày (mục 4.6): ngày có hoàn tất lượt Ôn luyện, lượt ôn Sổ tay, hoặc nộp Thi thử có ít nhất 1 câu trả lời.
    Tính theo ngày của máy chủ; hôm nay chưa học thì chuỗi vẫn giữ nếu hôm qua có học; bỏ trọn một ngày thì về 0."""
    today = db.execute(text("SELECT CURDATE()")).scalar_one()
    days = [r[0] for r in db.execute(
        text("""SELECT DISTINCT DATE(l.nop_luc) AS d FROM luot_lam l LEFT JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.nguoi_dung_id = :u AND l.trang_thai = 'da_nop' AND l.nop_luc IS NOT NULL
                  AND (b.loai IN ('bai', 'cuoi_thua') OR l.loai_boc_cau = 'so_tay'
                       OR EXISTS(SELECT 1 FROM cau_tra_loi a WHERE a.luot_lam_id = l.id
                                 AND (a.phuong_an_chon_id IS NOT NULL OR a.van_ban IS NOT NULL)))
                ORDER BY d DESC LIMIT 400"""),
        {"u": uid},
    ).all()]
    if not days or (today - days[0]).days > 1:
        return 0
    count, expected = 0, days[0]
    for d in days:
        if d != expected:
            break
        count += 1
        expected = d - timedelta(days=1)
    return count


def energy_and_kn(db: Session, uid: int) -> dict:
    row = db.execute(
        text("""SELECT n.nang_luong,
                       (SELECT COALESCE(SUM(so_luong), 0) FROM nhat_ky_thuong t WHERE t.nguoi_dung_id = n.id AND t.ly_do LIKE 'kn\\_%') AS kn
                FROM nguoi_dung n WHERE n.id = :u"""),
        {"u": uid},
    ).mappings().one()
    return {"nang_luong": int(row["nang_luong"]), "nang_luong_toi_da": 5, "kn": int(row["kn"]), "chuoi_ngay": streak_days(db, uid)}


def overview(db: Session, uid: int) -> dict:
    lv = levels(db)
    skills = []
    for skill in SKILLS:
        opened = opened_levels(db, uid, skill, lv)
        mine = [l for l in lv if level_open(l, skill, opened)]
        # cấp đang học: cấp mở cao nhất (đã mở bằng kiểm tra thì học tiếp ở đó)
        level = mine[-1] if mine else None
        if level is None:
            skills.append({"ky_nang": skill, "cap_do": None, "so_bai": 0, "da_xong": 0, "bai_tiep": None})
            continue
        s = summarize(build_map(db, uid, level["id"], skill))
        skills.append({"ky_nang": skill, "cap_do": {"id": level["id"], "ten": level["ten"]}, **s})
    return {**energy_and_kn(db, uid), "ky_nang": skills}


def skill_levels(db: Session, skill: str) -> list[dict]:
    """Cấp có kỹ năng này: Viết chỉ từ HSK 3 trở lên, các kỹ năng khác từ HSK 1."""
    return [l for l in levels(db) if l["thu_tu"] >= START_ORDER[skill]]


def skill_path(db: Session, uid: int, skill: str, cap_do_id: int | None) -> dict:
    from app.modules.practice.services import level_test_service  # tránh vòng import

    lv = skill_levels(db, skill)
    opened = opened_levels(db, uid, skill, lv)
    passed = level_tests(db, uid, skill)
    tabs = []
    for level in lv:
        is_open = level_open(level, skill, opened)
        info = {"id": level["id"], "ten": level["ten"], "mo": is_open}
        if is_open:
            info.update(summarize(build_map(db, uid, level["id"], skill)))
        tabs.append(info)
    chosen = next((l for l in lv if l["id"] == cap_do_id), None) if cap_do_id else None
    if chosen is None:
        mine = [l for l in lv if level_open(l, skill, opened)]
        chosen = mine[-1] if mine else (lv[0] if lv else None)
    chosen_open = bool(chosen) and level_open(chosen, skill, opened)
    if chosen_open:
        lands = build_map(db, uid, chosen["id"], skill)
    else:  # cấp chưa mở: vẫn cho xem trước các thửa, mọi ô khóa
        lands = [locked_preview(land) for land in build_map(db, 0, chosen["id"], skill)] if chosen else []
    test = None
    lands_for_test = lands if chosen_open else []
    if chosen:
        test = (level_test_service.stage_info(db, uid, skill, chosen, lv, lands_for_test, passed) if chosen_open
                else level_test_service.start_info(db, uid, skill, chosen, lv))
    return {
        **energy_and_kn(db, uid), "ky_nang": skill, "cap_do": chosen and {"id": chosen["id"], "ten": chosen["ten"], "mo": chosen_open},
        "cap": tabs, "thua": lands, "kiem_tra_cap": test,
        **({"bai_tiep": summarize(lands)["bai_tiep"]} if lands and chosen_open else {"bai_tiep": None}),
    }


def locked_preview(land: dict) -> dict:
    """Thửa của cấp chưa mở: giữ tên/mục tiêu để xem trước, mọi ô khóa, không có tiến độ."""
    slots = [o if o["trang_thai"] == "chua_xuat_ban" else {**o, "trang_thai": "khoa", "luot_dang_lam": None} for o in land["o"]]
    return {**land, "mo": False, "da_vuot": False, "thu_hoach": False, "o": slots}
