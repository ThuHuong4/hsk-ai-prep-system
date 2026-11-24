from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError
from app.modules.grading import correct_option_id, load_set_items as load_items

SKILL = {"nghe": "Nghe", "doc": "Đọc", "viet": "Viết", "tu_vung": "Từ vựng"}
TYPE = {
    "chon_mot": "chọn một đáp án", "dung_sai": "đúng/sai", "chon_bo_chung": "chọn từ bộ phương án chung",
    "sap_xep": "sắp xếp câu", "dien_chu": "điền chữ", "viet_mo": "viết câu", "dich_cau": "dịch câu",
}
LETTERS = "ABCDEFGH"


def _attempt(db: Session, luot_id: int, uid: int) -> dict:
    row = db.execute(
        text("""SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.trang_thai, b.loai, c.ten AS ten_cap_do
                FROM luot_lam l
                JOIN bo_de b ON b.id = l.bo_de_id
                LEFT JOIN bo_de t ON t.ma_goc_id = b.thua_id AND t.trang_thai = 'da_dang'
                LEFT JOIN cap_do c ON c.id = COALESCE(b.cap_do_id, t.cap_do_id)
                WHERE l.id = :id"""),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:  # Lượt của người khác: coi như không tồn tại
        raise NotFoundError()
    return dict(row)


def _answer(db: Session, luot_id: int, cau_hoi_id: int) -> dict:
    row = db.execute(
        text("""SELECT a.phuong_an_chon_id, a.van_ban, a.trang_thai_thao_tac, a.xac_nhan_luc, v.diem
                FROM cau_tra_loi a LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                WHERE a.luot_lam_id = :l AND a.cau_hoi_id = :q"""),
        {"l": luot_id, "q": cau_hoi_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError()
    return dict(row)


def _option_text(o: dict, index: int) -> str:
    label = LETTERS[index] if index < len(LETTERS) else str(index + 1)
    content = (o["noi_dung"] or "").strip() or "(phương án là hình, không có chữ)"
    return f"{label}. {content}"


def build_context(db: Session, uid: int, luot_id: int, cau_hoi_id: int) -> str:
    attempt = _attempt(db, luot_id, uid)
    practice = attempt["loai"] in ("bai", "cuoi_thua")
    if practice is False and attempt["loai"] != "de_thi":
        raise NotFoundError()

    answer = _answer(db, luot_id, cau_hoi_id)
    if practice and answer["xac_nhan_luc"] is None:
        raise ConflictError("Hãy bấm Kiểm tra trước khi hỏi Xiang về câu này")
    if practice and answer.get("trang_thai_thao_tac") == "bo_qua":
        raise ConflictError("Câu đã bỏ qua không mở Hỏi Xiang để tránh lộ đáp án")
    if not practice and attempt["trang_thai"] != "da_nop":
        raise ConflictError("Hỏi Xiang mở sau khi nộp bài thi")

    _, questions, options = load_items(db, attempt["bo_de_id"])
    q = questions.get(cau_hoi_id)
    if q is None:
        raise NotFoundError()
    parent = questions.get(q["cau_cha_id"]) if q["cau_cha_id"] else None

    owner = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
    choices = options[owner]["lua_chon"]
    right_id = correct_option_id(q, options) if choices else None
    chosen_id = answer["phuong_an_chon_id"]

    lines = [
        f"Phần: {'Ôn luyện' if practice else 'Thi thử'} · {attempt['ten_cap_do'] or ''} · kỹ năng {SKILL.get(q['ky_nang'], q['ky_nang'])} · dạng {TYPE.get(q['dang'], q['dang'])}",
    ]
    if parent and (parent["noi_dung"] or parent["mo_ta_hinh"]):
        lines.append(f"Ngữ liệu chung: {parent['noi_dung'] or ''} {('(hình: ' + parent['mo_ta_hinh'] + ')') if parent['mo_ta_hinh'] else ''}".strip())
    if q["noi_dung"]:
        lines.append(f"Đề: {q['noi_dung']}")
    if q["pinyin"]:
        lines.append(f"Pinyin của đề: {q['pinyin']}")
    if q["mo_ta_hinh"]:
        lines.append(f"Mô tả hình của đề: {q['mo_ta_hinh']}")
    if q["loi_nghe"]:
        lines.append(f"Lời nghe (kịch bản audio): {q['loi_nghe']}")
    if choices:
        lines.append("Các phương án:")
        lines += [f"  {_option_text(o, i)}" for i, o in enumerate(choices)]
        pick = next((i for i, o in enumerate(choices) if o["id"] == chosen_id), None)
        right = next((i for i, o in enumerate(choices) if o["id"] == right_id), None)
        lines.append(f"Học viên chọn: {_option_text(choices[pick], pick) if pick is not None else 'bỏ trống'}")
        if right is not None:
            lines.append(f"Đáp án đúng: {_option_text(choices[right], right)}")
    else:
        lines.append(f"Học viên trả lời: {answer['van_ban'] or 'bỏ trống'}")
        accepted = [o["noi_dung"] for o in options[q["id"]]["chap_nhan"] if o["noi_dung"]]
        if accepted:
            lines.append(f"Đáp án chấp nhận: {' / '.join(accepted)}")
    if answer["diem"] is None:
        lines.append("Kết quả: chưa chấm xong")
    else:
        pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
        lines.append(f"Kết quả: {'đúng' if float(answer['diem']) >= pass_mark else 'sai'}")
    if q["dich_nghia"]:
        lines.append(f"Dịch nghĩa: {q['dich_nghia']}")
    if q["giai_thich"]:
        lines.append(f"Giải thích của Giảng viên: {q['giai_thich']}")
    return "\n".join(lines)