"""Nạp lộ trình Ôn luyện Từ vựng HSK 3 (3 thửa, 60 từ) dưới tên một tài khoản Giảng viên.

Nguồn từ: danh sách từ vựng HSK 3 (hệ HSK 2.0, 6 cấp) của 国家汉办/孔子学院总部; chọn 60 từ có nghĩa cụ thể.
Nghĩa tiếng Việt và câu hỏi do Xianglingo tự soạn (không chép ngân hàng câu hỏi của trang khác).

Cách dùng (trong thư mục backend):  python scripts/seed_hsk3_tu_vung.py <email Giảng viên>

- Mỗi thửa: Bài 1–4 (5 câu: nhìn từ chọn nghĩa) + Kiểm tra cuối thửa (10 câu: nhìn nghĩa chọn từ), đúng mục 4.1.
- Câu chỉ dùng cho Ôn luyện. Mỗi câu gắn một từ (mục 4.3); từ chưa có thì tạo và xuất bản, đã có thì dùng lại.
- Thửa cùng tên đã có ở HSK 3 – Từ vựng thì bỏ qua (không nạp trùng).
"""
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

# Mỗi thửa 4 bài × 5 từ: (chữ Hán, pinyin, nghĩa)
TU_VUNG = [
    {
        "ten": "Cơ thể, sức khỏe và tính cách",
        "muc_tieu": "Nhận biết từ chỉ bộ phận cơ thể, sức khỏe, ngoại hình và cảm xúc",
        "bai": [
            ("Bộ phận cơ thể", [("鼻子", "bízi", "mũi"), ("耳朵", "ěrduo", "tai"), ("头发", "tóufa", "tóc"),
                                ("腿", "tuǐ", "chân (phần cẳng, đùi)"), ("嘴", "zuǐ", "miệng")]),
            ("Sức khỏe", [("感冒", "gǎnmào", "bị cảm"), ("发烧", "fāshāo", "sốt"), ("疼", "téng", "đau"),
                          ("健康", "jiànkāng", "khỏe mạnh"), ("锻炼", "duànliàn", "rèn luyện thân thể")]),
            ("Ngoại hình và tính cách", [("矮", "ǎi", "thấp (chiều cao)"), ("胖", "pàng", "béo"), ("瘦", "shòu", "gầy"),
                                         ("聪明", "cōngming", "thông minh"), ("可爱", "kě'ài", "đáng yêu")]),
            ("Cảm xúc", [("担心", "dānxīn", "lo lắng"), ("害怕", "hàipà", "sợ"), ("生气", "shēngqì", "tức giận"),
                         ("满意", "mǎnyì", "hài lòng"), ("着急", "zháojí", "sốt ruột")]),
        ],
    },
    {
        "ten": "Nhà cửa và đồ dùng",
        "muc_tieu": "Nhận biết từ về đồ dùng trong nhà, quần áo, đồ cá nhân và việc nhà",
        "bai": [
            ("Đồ dùng trong nhà", [("冰箱", "bīngxiāng", "tủ lạnh"), ("空调", "kōngtiáo", "điều hòa"), ("灯", "dēng", "đèn"),
                                   ("碗", "wǎn", "cái bát"), ("筷子", "kuàizi", "đũa")]),
            ("Quần áo", [("衬衫", "chènshān", "áo sơ mi"), ("裤子", "kùzi", "quần"), ("裙子", "qúnzi", "váy"),
                         ("帽子", "màozi", "mũ"), ("皮鞋", "píxié", "giày da")]),
            ("Đồ dùng cá nhân", [("伞", "sǎn", "ô, dù"), ("护照", "hùzhào", "hộ chiếu"), ("照相机", "zhàoxiàngjī", "máy ảnh"),
                                 ("行李箱", "xínglixiāng", "va li"), ("笔记本", "bǐjìběn", "sổ ghi chép")]),
            ("Việc nhà", [("打扫", "dǎsǎo", "quét dọn"), ("洗澡", "xǐzǎo", "tắm"), ("刷牙", "shuāyá", "đánh răng"),
                          ("搬", "bān", "chuyển, dọn (nhà)"), ("照顾", "zhàogu", "chăm sóc")]),
        ],
    },
    {
        "ten": "Thành phố, thiên nhiên và trường học",
        "muc_tieu": "Nhận biết từ về địa điểm trong thành phố, mùa, động thực vật và môn học",
        "bai": [
            ("Thành phố", [("超市", "chāoshì", "siêu thị"), ("银行", "yínháng", "ngân hàng"), ("图书馆", "túshūguǎn", "thư viện"),
                           ("地铁", "dìtiě", "tàu điện ngầm"), ("电梯", "diàntī", "thang máy")]),
            ("Bốn mùa", [("春", "chūn", "mùa xuân"), ("夏", "xià", "mùa hè"), ("秋", "qiū", "mùa thu"),
                         ("冬", "dōng", "mùa đông"), ("太阳", "tàiyáng", "mặt trời")]),
            ("Động vật và cây cỏ", [("熊猫", "xióngmāo", "gấu trúc"), ("鸟", "niǎo", "con chim"), ("马", "mǎ", "con ngựa"),
                                    ("树", "shù", "cái cây"), ("草", "cǎo", "cỏ")]),
            ("Trường học", [("数学", "shùxué", "môn toán"), ("历史", "lìshǐ", "lịch sử"), ("作业", "zuòyè", "bài tập về nhà"),
                            ("复习", "fùxí", "ôn tập"), ("成绩", "chéngjì", "thành tích, điểm số")]),
        ],
    },
]


def place(options: list[str], correct_index: int, slot: int) -> tuple[list[str], int]:
    """Đưa phương án đúng tới vị trí slot (0–2) để đáp án không luôn là A."""
    right = options[correct_index]
    others = [o for i, o in enumerate(options) if i != correct_index]
    others.insert(slot % len(options), right)
    return others, slot % len(options)


def mc(opts: list[str], answer: int) -> list[dict]:
    return [{"noi_dung": o, "la_dap_an_dung": i == answer} for i, o in enumerate(opts)]


def word_id(db, level: int, uid: int, han: str, py: str, nghia: str, created: list) -> int:
    row = db.execute(text("SELECT id, trang_thai, cap_do_id FROM tu_vung WHERE chu_han = :h AND pinyin = :p"),
                     {"h": han, "p": py}).mappings().first()
    if row:
        if row["cap_do_id"] != level:
            raise SystemExit(f"✗ Từ {han} ({py}) đã có nhưng thuộc cấp khác; dừng để không sửa dữ liệu của bạn")
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


def build_land(db, uid: int, level: int, land: dict, lessons: list, final: list[int]) -> None:
    land_id = path_service.create_land(db, SimpleNamespace(cap_do_id=level, ky_nang="tu_vung", ten=land["ten"],
                                                           muc_tieu=land["muc_tieu"]), uid)
    for pos, (name, qids) in enumerate(lessons + [("Kiểm tra cuối thửa", final)], start=1):
        lesson_id = path_service.create_lesson(db, SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=name,
                                                                   muc_tieu=None, tai_lieu_id=None), uid)
        path_service.set_lesson_items(db, lesson_id, [SimpleNamespace(cau_hoi_id=q) for q in qids])
        path_service.lesson_status(db, lesson_id, "dang")
    path_service.land_status(db, land_id, "dang")
    print(f"→ Từ vựng HSK 3 · {land['ten']}: {sum(len(q) for _, q in lessons)} câu bài + {len(final)} câu cuối thửa, đã đăng")


def land_exists(db, level: int, name: str) -> bool:
    return bool(db.execute(
        text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'tu_vung' AND ten = :t LIMIT 1"),
        {"c": level, "t": name},
    ).first())


def seed_land(db, uid: int, level: int, land: dict) -> None:
    if land_exists(db, level, land["ten"]):
        print(f"· Bỏ qua Từ vựng HSK 3 · {land['ten']} (đã có)")
        return
    created: list[str] = []
    words = [[(word_id(db, level, uid, h, p, n, created), h, p, n) for h, p, n in ws] for _, ws in land["bai"]]
    db.commit()
    base = {"dang": "chon_mot", "cap_do_id": level, "ky_nang": "tu_vung", "dung_on_luyen": True, "dung_thi_thu": False}
    lessons, n = [], 0
    for (name, _), group in zip(land["bai"], words):
        qids = []
        for i, (wid, h, p, nghia) in enumerate(group):
            opts, ans = place([nghia, group[(i + 1) % 5][3], group[(i + 2) % 5][3]], 0, n)
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
        opts, ans = place([f"{h} [{p}]", f"{a[1]} [{a[2]}]", f"{b[1]} [{b[2]}]"], 0, k + 1)
        final.append(new_question(db, uid, {
            **base, "tu_vung_id": wid, "noi_dung": f"Từ nào có nghĩa là “{nghia}”?", "dich_nghia": f"{h} ({p}): {nghia}",
            "giai_thich": f"“{nghia}” là {h} ({p}).", "phuong_an": mc(opts, ans),
        }))
    if created:
        print(f"  + Tạo và xuất bản {len(created)} từ mới")
    build_land(db, uid, level, land, lessons, final)


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/seed_hsk3_tu_vung.py <email Giảng viên>")
        return 1
    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[1].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        level = db.execute(text("SELECT id FROM cap_do WHERE ma = 'HSK3'")).scalar_one_or_none()
        if level is None:
            print("✗ Chưa có cấp HSK3 trong bảng cap_do")
            return 1
        db.rollback()
        for land in TU_VUNG:
            seed_land(db, uid, level, land)
        print("Xong.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
