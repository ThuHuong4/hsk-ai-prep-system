"""Nạp lộ trình Ôn luyện HSK 1 mẫu (Từ vựng 2 thửa, Đọc 1 thửa) dưới tên một tài khoản Giảng viên.

Cách dùng (trong thư mục backend):  python scripts/seed_hsk1_on_luyen.py <email Giảng viên>

- Mỗi thửa: Bài 1–4 (5 câu) + Kiểm tra cuối thửa (10 câu), đúng quy tắc mục 4.1.
- Câu chỉ dùng cho Ôn luyện (không dùng Thi thử). Câu Từ vựng gắn một từ (mục 4.3).
- Từ vựng: từ chưa có thì tạo và xuất bản; từ đã có thì dùng lại, không sửa.
- Thửa đã có cùng tên ở HSK 1 + kỹ năng đó thì bỏ qua thửa đó (không nạp trùng).
- Nghe chưa nạp vì chưa có file âm thanh cho từng câu.
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

# ---------------------------------------------------------------- Từ vựng
# Mỗi thửa 4 bài × 5 từ: (chữ Hán, pinyin, nghĩa)
TU_VUNG = [
    {
        "ten": "Chào hỏi và gia đình",
        "muc_tieu": "Nhận biết đại từ, lời chào và từ chỉ người trong gia đình",
        "bai": [
            ("Đại từ nhân xưng", [("你", "nǐ", "bạn, anh, chị (ngôi thứ hai)"), ("我", "wǒ", "tôi"), ("他", "tā", "anh ấy, ông ấy"),
                                  ("她", "tā", "cô ấy, bà ấy"), ("我们", "wǒmen", "chúng tôi, chúng ta")]),
            ("Lời chào và cảm ơn", [("谢谢", "xièxie", "cảm ơn"), ("不客气", "bú kèqi", "không có gì, đừng khách sáo"),
                                    ("再见", "zàijiàn", "tạm biệt"), ("对不起", "duìbuqǐ", "xin lỗi"), ("没关系", "méi guānxi", "không sao")]),
            ("Gia đình", [("爸爸", "bàba", "bố"), ("妈妈", "māma", "mẹ"), ("儿子", "érzi", "con trai"),
                          ("女儿", "nǚ'ér", "con gái"), ("家", "jiā", "nhà, gia đình")]),
            ("Bạn bè và nghề nghiệp", [("朋友", "péngyou", "bạn bè"), ("老师", "lǎoshī", "giáo viên"), ("学生", "xuésheng", "học sinh"),
                                       ("医生", "yīshēng", "bác sĩ"), ("同学", "tóngxué", "bạn học")]),
        ],
    },
    {
        "ten": "Số đếm và thời gian",
        "muc_tieu": "Nhận biết số từ 1 đến 10 và các từ chỉ thời gian",
        "bai": [
            ("Số 1–5", [("一", "yī", "một (1)"), ("二", "èr", "hai (2)"), ("三", "sān", "ba (3)"), ("四", "sì", "bốn (4)"), ("五", "wǔ", "năm (5)")]),
            ("Số 6–10", [("六", "liù", "sáu (6)"), ("七", "qī", "bảy (7)"), ("八", "bā", "tám (8)"), ("九", "jiǔ", "chín (9)"), ("十", "shí", "mười (10)")]),
            ("Hôm nay, ngày mai", [("今天", "jīntiān", "hôm nay"), ("明天", "míngtiān", "ngày mai"), ("昨天", "zuótiān", "hôm qua"),
                                   ("现在", "xiànzài", "bây giờ"), ("星期", "xīngqī", "tuần, thứ (trong tuần)")]),
            ("Năm, tháng, giờ", [("年", "nián", "năm (đơn vị thời gian)"), ("月", "yuè", "tháng"), ("号", "hào", "ngày (trong tháng)"),
                                 ("点", "diǎn", "giờ (trên đồng hồ)"), ("分钟", "fēnzhōng", "phút")]),
        ],
    },
]

# ---------------------------------------------------------------- Đọc
# (câu hỏi, pinyin, [phương án], vị trí đáp án đúng 0-2, dịch nghĩa, giải thích)
# Chữ Hán và pinyin tách từ bằng dấu cách, cùng số từ; "_" = chỗ trống không có pinyin.
DOC = {
    "ten": "Chào hỏi và giới thiệu",
    "muc_tieu": "Đọc hiểu lời chào, câu giới thiệu bản thân và câu hỏi ngắn",
    "bai": [
        ("Lời chào", [
            ("你 （　）！", "Nǐ _", ["好 [hǎo]", "是 [shì]", "叫 [jiào]"], 0, "Xin chào!", "你好 = xin chào."),
            ("谢谢 你！\n不 （　）。", "Xièxie nǐ!\nBù _", ["客气 [kèqi]", "认识 [rènshi]", "漂亮 [piàoliang]"], 0,
             "Cảm ơn bạn! – Không có gì.", "Đáp lại lời cảm ơn: 不客气 (đừng khách sáo)."),
            ("对不起！\n没 （　）。", "Duìbuqǐ!\nMéi _", ["关系 [guānxi]", "什么 [shénme]", "名字 [míngzi]"], 0,
             "Xin lỗi! – Không sao.", "Đáp lại lời xin lỗi: 没关系 (không sao)."),
            ("明天 （　）！", "Míngtiān _", ["见 [jiàn]", "去 [qù]", "看 [kàn]"], 0, "Hẹn gặp ngày mai!", "明天见 = mai gặp lại."),
            ("认识 你， 很 （　）。", "Rènshi nǐ, hěn _", ["高兴 [gāoxìng]", "喜欢 [xǐhuan]", "热 [rè]"], 0,
             "Rất vui được làm quen với bạn.", "很高兴 = rất vui."),
        ]),
        ("Giới thiệu bản thân", [
            ("我 （　） 王 明。", "Wǒ _ Wáng Míng.", ["叫 [jiào]", "有 [yǒu]", "在 [zài]"], 0, "Tôi tên là Vương Minh.", "叫 + tên = tên là."),
            ("你 叫 什么 （　）？", "Nǐ jiào shénme _", ["名字 [míngzi]", "东西 [dōngxi]", "时候 [shíhou]"], 0,
             "Bạn tên là gì?", "叫什么名字 = tên là gì."),
            ("我 是 中国 （　）。", "Wǒ shì Zhōngguó _", ["人 [rén]", "字 [zì]", "菜 [cài]"], 0, "Tôi là người Trung Quốc.", "中国人 = người Trung Quốc."),
            ("她 是 我 的 （　）， 我们 是 同学。", "Tā shì wǒ de _, wǒmen shì tóngxué.", ["朋友 [péngyou]", "爸爸 [bàba]", "医生 [yīshēng]"], 0,
             "Cô ấy là bạn của tôi, chúng tôi là bạn học.", "Câu sau nói 我们是同学 nên chọn 朋友 (bạn)."),
            ("我 （　） 北京 人。", "Wǒ _ Běijīng rén.", ["是 [shì]", "叫 [jiào]", "去 [qù]"], 0, "Tôi là người Bắc Kinh.", "是 = là."),
        ]),
        ("Hỏi và trả lời", [
            ("你 好 吗？", "Nǐ hǎo ma?", ["我 很 好， 谢谢。 [Wǒ hěn hǎo, xièxie.]", "我 是 老师。 [Wǒ shì lǎoshī.]", "他 是 我 爸爸。 [Tā shì wǒ bàba.]"], 0,
             "Bạn khỏe không? – Tôi rất khỏe, cảm ơn.", "Hỏi thăm sức khỏe thì trả lời 我很好."),
            ("你 叫 什么 名字？", "Nǐ jiào shénme míngzi?", ["我 叫 李 月。 [Wǒ jiào Lǐ Yuè.]", "我 今年 八 岁。 [Wǒ jīnnián bā suì.]", "我 在 学校。 [Wǒ zài xuéxiào.]"], 0,
             "Bạn tên là gì? – Tôi tên là Lý Nguyệt.", "Hỏi tên thì trả lời 我叫…"),
            ("你 是 哪 国 人？", "Nǐ shì nǎ guó rén?", ["我 是 中国 人。 [Wǒ shì Zhōngguó rén.]", "我 是 学生。 [Wǒ shì xuésheng.]", "我 去 中国。 [Wǒ qù Zhōngguó.]"], 0,
             "Bạn là người nước nào? – Tôi là người Trung Quốc.", "哪国人 hỏi quốc tịch."),
            ("她 是 谁？", "Tā shì shéi?", ["她 是 我 妈妈。 [Tā shì wǒ māma.]", "她 很 漂亮。 [Tā hěn piàoliang.]", "她 在 家。 [Tā zài jiā.]"], 0,
             "Cô ấy là ai? – Cô ấy là mẹ tôi.", "谁 hỏi là ai."),
            ("你 认识 他 吗？", "Nǐ rènshi tā ma?", ["认识， 他 是 我 同学。 [Rènshi, tā shì wǒ tóngxué.]", "他 是 医生。 [Tā shì yīshēng.]", "他 不 在 家。 [Tā bú zài jiā.]"], 0,
             "Bạn có quen anh ấy không? – Có, anh ấy là bạn học của tôi.", "Hỏi 认识…吗 thì trả lời 认识 / 不认识."),
        ]),
        ("Hiểu câu ngắn", [
            ("我 爸爸 是 医生。", "Wǒ bàba shì yīshēng.", ["Bố tôi là bác sĩ.", "Mẹ tôi là bác sĩ.", "Bố tôi là giáo viên."], 0,
             "Bố tôi là bác sĩ.", "爸爸 = bố, 医生 = bác sĩ."),
            ("这 是 我 的 朋友。", "Zhè shì wǒ de péngyou.", ["Đây là bạn của tôi.", "Kia là bố của tôi.", "Đây là sách của tôi."], 0,
             "Đây là bạn của tôi.", "这 = đây, 朋友 = bạn."),
            ("她 不 是 老师， 她 是 学生。", "Tā bú shì lǎoshī, tā shì xuésheng.", ["Cô ấy là học sinh.", "Cô ấy là giáo viên.", "Cô ấy là bác sĩ."], 0,
             "Cô ấy không phải giáo viên, cô ấy là học sinh.", "不是 = không phải."),
            ("我 女儿 今年 五 岁。", "Wǒ nǚ'ér jīnnián wǔ suì.", ["Con gái tôi năm nay 5 tuổi.", "Con trai tôi năm nay 5 tuổi.", "Con gái tôi năm nay 15 tuổi."], 0,
             "Con gái tôi năm nay 5 tuổi.", "女儿 = con gái, 五岁 = 5 tuổi."),
            ("我们 都 是 中国 人。", "Wǒmen dōu shì Zhōngguó rén.", ["Chúng tôi đều là người Trung Quốc.", "Chúng tôi đều là học sinh.", "Chúng tôi đi Trung Quốc."], 0,
             "Chúng tôi đều là người Trung Quốc.", "都 = đều."),
        ]),
    ],
    "cuoi_thua": [
        ("你 （　） 几 岁？", "Nǐ _ jǐ suì?", ["今年 [jīnnián]", "名字 [míngzi]", "朋友 [péngyou]"], 0, "Năm nay bạn mấy tuổi?", "今年 = năm nay."),
        ("我 很 （　） 你。", "Wǒ hěn _ nǐ.", ["喜欢 [xǐhuan]", "高兴 [gāoxìng]", "叫 [jiào]"], 0, "Tôi rất thích bạn.", "喜欢 + người/vật = thích."),
        ("谢谢 你！", "Xièxie nǐ!", ["不 客气。 [Bú kèqi.]", "没 关系。 [Méi guānxi.]", "我 很 好。 [Wǒ hěn hǎo.]"], 0,
         "Cảm ơn bạn! – Không có gì.", "Đáp lại 谢谢 bằng 不客气."),
        ("对不起！", "Duìbuqǐ!", ["没 关系。 [Méi guānxi.]", "不 客气。 [Bú kèqi.]", "我 叫 王 明。 [Wǒ jiào Wáng Míng.]"], 0,
         "Xin lỗi! – Không sao.", "Đáp lại 对不起 bằng 没关系."),
        ("他 是 谁？", "Tā shì shéi?", ["他 是 我 的 老师。 [Tā shì wǒ de lǎoshī.]", "他 很 好。 [Tā hěn hǎo.]", "他 在 学校。 [Tā zài xuéxiào.]"], 0,
         "Anh ấy là ai? – Anh ấy là thầy giáo của tôi.", "谁 hỏi là ai."),
        ("你 是 学生 吗？", "Nǐ shì xuésheng ma?", ["是， 我 是 学生。 [Shì, wǒ shì xuésheng.]", "我 叫 李 月。 [Wǒ jiào Lǐ Yuè.]", "我 是 中国 人。 [Wǒ shì Zhōngguó rén.]"], 0,
         "Bạn là học sinh à? – Vâng, tôi là học sinh.", "Câu hỏi 是…吗 trả lời 是 / 不是."),
        ("我 儿子 是 学生。", "Wǒ érzi shì xuésheng.", ["Con trai tôi là học sinh.", "Con gái tôi là học sinh.", "Con trai tôi là giáo viên."], 0,
         "Con trai tôi là học sinh.", "儿子 = con trai."),
        ("他们 是 我 的 同学。", "Tāmen shì wǒ de tóngxué.", ["Họ là bạn học của tôi.", "Họ là thầy giáo của tôi.", "Chúng tôi là bạn học."], 0,
         "Họ là bạn học của tôi.", "他们 = họ, 同学 = bạn học."),
        ("我 （　） 王 老师。", "Wǒ _ Wáng lǎoshī.", ["认识 [rènshi]", "高兴 [gāoxìng]", "客气 [kèqi]"], 0, "Tôi quen thầy Vương.", "认识 = quen biết."),
        ("她 是 我 的 （　）， 她 很 漂亮。", "Tā shì wǒ de _, tā hěn piàoliang.", ["女儿 [nǚ'ér]", "儿子 [érzi]", "爸爸 [bàba]"], 0,
         "Cô ấy là con gái tôi, cô ấy rất xinh.", "她 (cô ấy) nên chọn 女儿 (con gái)."),
    ],
}


def place(options: list[str], correct_index: int, slot: int) -> tuple[list[str], int]:
    """Đưa phương án đúng tới vị trí slot (0–2) để đáp án không luôn là A."""
    right = options[correct_index]
    others = [o for i, o in enumerate(options) if i != correct_index]
    others.insert(slot % len(options), right)
    return others, slot % len(options)


def mc(opts: list[str], answer: int) -> list[dict]:
    return [{"noi_dung": o, "la_dap_an_dung": i == answer} for i, o in enumerate(opts)]


def word_id(db, level: int, uid: int, han: str, py: str, nghia: str, created: list) -> int:
    row = db.execute(text("SELECT id, trang_thai, cap_do_id FROM tu_vung WHERE chu_han = :h AND pinyin = :p"), {"h": han, "p": py}).mappings().first()
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


def build_land(db, uid: int, level: int, skill: str, land: dict, lessons: list[tuple[str, list[int]]], final: list[int]) -> None:
    land_id = path_service.create_land(db, SimpleNamespace(cap_do_id=level, ky_nang=skill, ten=land["ten"], muc_tieu=land["muc_tieu"]), uid)
    for pos, (name, qids) in enumerate(lessons + [("Kiểm tra cuối thửa", final)], start=1):
        lesson_id = path_service.create_lesson(db, SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=name, muc_tieu=None, tai_lieu_id=None), uid)
        path_service.set_lesson_items(db, lesson_id, [SimpleNamespace(cau_hoi_id=q) for q in qids])
        path_service.lesson_status(db, lesson_id, "dang")
    path_service.land_status(db, land_id, "dang")
    print(f"→ {skill} · {land['ten']}: {sum(len(q) for _, q in lessons)} câu bài + {len(final)} câu cuối thửa, đã đăng")


def land_exists(db, level: int, skill: str, name: str) -> bool:
    return bool(db.execute(
        text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = :k AND ten = :t LIMIT 1"),
        {"c": level, "k": skill, "t": name},
    ).first())


def seed_vocabulary(db, uid: int, level: int) -> None:
    for land in TU_VUNG:
        if land_exists(db, level, "tu_vung", land["ten"]):
            print(f"· Bỏ qua Từ vựng · {land['ten']} (đã có)")
            continue
        created: list[str] = []
        words = [[(word_id(db, level, uid, h, p, n, created), h, p, n) for h, p, n in ws] for _, ws in land["bai"]]
        db.commit()
        lessons, n = [], 0
        for (name, _), group in zip(land["bai"], words):
            qids = []
            for i, (wid, h, p, nghia) in enumerate(group):
                opts = [nghia, group[(i + 1) % 5][3], group[(i + 2) % 5][3]]
                opts, ans = place(opts, 0, n)
                n += 1
                qids.append(new_question(db, uid, {
                    "dang": "chon_mot", "cap_do_id": level, "ky_nang": "tu_vung", "dung_on_luyen": True, "dung_thi_thu": False,
                    "tu_vung_id": wid, "noi_dung": h, "pinyin": p.replace(" ", ""), "dich_nghia": f"{h} ({p}): {nghia}",
                    "giai_thich": f"{h} đọc là {p}, nghĩa là “{nghia}”.", "phuong_an": mc(opts, ans),
                }))
            lessons.append((name, qids))
        flat = [w for group in words for w in group]
        final = []
        for k, idx in enumerate([0, 2, 5, 7, 10, 12, 15, 17, 3, 8]):
            wid, h, p, nghia = flat[idx]
            opts = [f"{h} [{p}]", f"{flat[(idx + 6) % 20][1]} [{flat[(idx + 6) % 20][2]}]", f"{flat[(idx + 13) % 20][1]} [{flat[(idx + 13) % 20][2]}]"]
            opts, ans = place(opts, 0, k + 1)
            final.append(new_question(db, uid, {
                "dang": "chon_mot", "cap_do_id": level, "ky_nang": "tu_vung", "dung_on_luyen": True, "dung_thi_thu": False,
                "tu_vung_id": wid, "noi_dung": f"Từ nào có nghĩa là “{nghia}”?", "dich_nghia": f"{h} ({p}): {nghia}",
                "giai_thich": f"“{nghia}” là {h} ({p}).", "phuong_an": mc(opts, ans),
            }))
        if created:
            print(f"  + Tạo và xuất bản {len(created)} từ mới")
        build_land(db, uid, level, "tu_vung", land, lessons, final)


def seed_reading(db, uid: int, level: int) -> None:
    if land_exists(db, level, "doc", DOC["ten"]):
        print(f"· Bỏ qua Đọc · {DOC['ten']} (đã có)")
        return
    n = 0

    def make(item) -> int:
        nonlocal n
        stem, py, opts, answer, vi, why = item
        opts, ans = place(opts, answer, n)
        n += 1
        return new_question(db, uid, {
            "dang": "chon_mot", "cap_do_id": level, "ky_nang": "doc", "dung_on_luyen": True, "dung_thi_thu": False,
            "noi_dung": stem, "pinyin": py, "dich_nghia": vi, "giai_thich": why, "phuong_an": mc(opts, ans),
        })

    lessons = [(name, [make(x) for x in items]) for name, items in DOC["bai"]]
    final = [make(x) for x in DOC["cuoi_thua"]]
    build_land(db, uid, level, "doc", DOC, lessons, final)


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/seed_hsk1_on_luyen.py <email Giảng viên>")
        return 1
    db = SessionLocal()
    try:
        uid = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                         {"e": sys.argv[1].strip().lower()}).scalar_one_or_none()
        if uid is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        level = db.execute(text("SELECT id FROM cap_do WHERE ma = 'HSK1'")).scalar_one_or_none()
        if level is None:
            print("✗ Chưa có cấp HSK1 trong bảng cap_do")
            return 1
        db.rollback()
        seed_vocabulary(db, uid, level)
        seed_reading(db, uid, level)
        print("Xong. Nghe chưa nạp (cần file âm thanh từng câu).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
