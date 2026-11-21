"""Nạp Đề 1 HSK 1 (mã H10000, nguồn Hanban/孔子学院总部 – HSK（一级）样卷) vào CSDL Xianglingo.

Tạo 40 câu + câu ví dụ (đã đăng, dùng cho Thi thử) và 1 đề thi thử đã đăng, mã H10000.
Hình lấy từ uploads/exams/hsk1_h10000/img, âm thanh chung uploads/exams/hsk1_h10000/listening.mp3.

Cách chạy (đứng trong thư mục backend):
    python scripts/seed_hsk1_h10000.py gv.test@gmail.com
(email là tài khoản Giảng viên đứng tên người tạo). Chạy lại khi đề đã có sẽ dừng, không tạo trùng.

Quy ước hiển thị: chữ Hán trong "noi_dung" tách từ bằng dấu cách, "pinyin" tách tương ứng
→ trang thi đặt pinyin trên từng từ; "_" = không có pinyin. Phương án có pinyin ghi "汉字 [pinyin]".
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemIn  # noqa: E402
from app.modules.exam_authoring.services import exam_service  # noqa: E402
from app.modules.questions.schemas.question_payload import QuestionIn  # noqa: E402
from app.modules.questions.services.question_status import publish_question  # noqa: E402
from app.modules.questions.services.save_question import create_question  # noqa: E402

CODE = "H10000"
IMG = "exams/hsk1_h10000/img/{}.jpg"
AUDIO = "exams/hsk1_h10000/listening.mp3"


def img(n: int) -> str:
    return IMG.format(f"{n:03d}")


def tf(correct: bool) -> list[dict]:
    return [{"noi_dung": "Đúng", "la_dap_an_dung": correct}, {"noi_dung": "Sai", "la_dap_an_dung": not correct}]


def pics(numbers: list[int], answer: int | None = None) -> list[dict]:
    return [{"tep_hinh": img(n), "la_dap_an_dung": answer == i} for i, n in enumerate(numbers)]


def words(items: list[str], answer: int | None = None) -> list[dict]:
    return [{"noi_dung": w, "la_dap_an_dung": answer == i} for i, w in enumerate(items)]


LETTER = {c: i + 1 for i, c in enumerate("ABCDEF")}


def z(value: str) -> str:
    """Tách token sau dấu phẩy/hai chấm toàn chiều để khớp số từ với pinyin."""
    return re.sub(r"([，：])(?=\S)", r"\1 ", value)

# ---------------------------------------------------------------- 一、听力
# Phần 1 (câu 1–5): nghe + hình → đúng/sai
L1 = [  # (ví dụ?, hình, đúng?, lời nghe, pinyin, dịch)
    (True, 0, True, "很 高兴", "hěn gāoxìng", "Rất vui."),
    (True, 1, False, "看 电影", "kàn diànyǐng", "Xem phim."),
    (False, 2, False, "坐 出租车", "zuò chūzūchē", "Đi taxi."),
    (False, 3, True, "明天 见", "míngtiān jiàn", "Ngày mai gặp."),
    (False, 4, True, "十二 点", "shí'èr diǎn", "12 giờ."),
    (False, 5, False, "喝 水", "hē shuǐ", "Uống nước."),
    (False, 6, False, "打 电话", "dǎ diànhuà", "Gọi điện thoại."),
]
# Phần 2 (câu 6–10): nghe → chọn hình A/B/C
L2 = [  # (ví dụ?, [hình A,B,C], đáp án, lời nghe, pinyin, dịch)
    (True, [7, 8, 9], "A", "这 是 我 的 书。", "Zhè shì wǒ de shū.", "Đây là sách của tôi."),
    (False, [10, 11, 12], "A", "你 的 衣服 很 漂亮。", "Nǐ de yīfu hěn piàoliang.", "Quần áo của bạn rất đẹp."),
    (False, [13, 14, 15], "C", "他们 在 工作。", "Tāmen zài gōngzuò.", "Họ đang làm việc."),
    (False, [16, 17, 18], "B", "我 朋友 是 老师。", "Wǒ péngyou shì lǎoshī.", "Bạn tôi là giáo viên."),
    (False, [19, 20, 21], "C", "李 小姐，请 坐。", "Lǐ xiǎojiě, qǐng zuò.", "Cô Lý, mời ngồi."),
    (False, [22, 23, 24], "B", "我 儿子 在 大学 读 书。", "Wǒ érzi zài dàxué dú shū.", "Con trai tôi học đại học."),
]
# Phần 3 (câu 11–15): 6 hình A–F, nghe hội thoại → ghép
L3_PICS = [25, 26, 27, 28, 29, 30]
L3 = [  # (ví dụ?, đáp án, lời nghe, pinyin, dịch)
    (True, "C", "女：你 好！\n男：你 好！ 很 高兴 认识 你。", "_ Nǐ hǎo!\n_ Nǐ hǎo! Hěn gāoxìng rènshi nǐ.", "Nữ: Chào anh! – Nam: Chào cô! Rất vui được làm quen."),
    (False, "D", "男：这个 椅子 多少 钱？\n女：七十 块。", "_ Zhège yǐzi duōshao qián?\n_ Qīshí kuài.", "Cái ghế này bao nhiêu tiền? – 70 tệ."),
    (False, "E", "女：他 会 开 车 吗？\n男：会，他 开 车 三 年 多 了。", "_ Tā huì kāi chē ma?\n_ Huì, tā kāi chē sān nián duō le.", "Anh ấy biết lái xe không? – Biết, lái hơn 3 năm rồi."),
    (False, "B", "男：你 去 哪儿 了？\n女：我 去 买了 些 东西。", "_ Nǐ qù nǎr le?\n_ Wǒ qù mǎile xiē dōngxi.", "Bạn đi đâu vậy? – Tôi đi mua ít đồ."),
    (False, "A", "女：今天 我 请 你 吃 饭。\n男：太 好 了，我 想 吃 中国 菜。", "_ Jīntiān wǒ qǐng nǐ chī fàn.\n_ Tài hǎo le, wǒ xiǎng chī Zhōngguó cài.", "Hôm nay tôi mời bạn ăn cơm. – Tuyệt, tôi muốn ăn món Trung Quốc."),
    (False, "F", "男：他们 是 谁？\n女：他们 三 个 都 是 我 的 学生。", "_ Tāmen shì shéi?\n_ Tāmen sān ge dōu shì wǒ de xuésheng.", "Họ là ai? – Cả ba đều là học sinh của tôi."),
]
# Phần 4 (câu 16–20): nghe câu + câu hỏi → chọn A/B/C (chữ có pinyin)
L4 = [  # (ví dụ?, phương án, đáp án, lời nghe, pinyin, dịch)
    (True, ["商店 [shāngdiàn]", "医院 [yīyuàn]", "学校 [xuéxiào]"], "A",
     "下午 我 去 商店，我 想 买 一些 水果。\n问：她 下午 去 哪里？",
     "Xiàwǔ wǒ qù shāngdiàn, wǒ xiǎng mǎi yìxiē shuǐguǒ.\n_ Tā xiàwǔ qù nǎlǐ?", "Chiều tôi đi cửa hàng mua hoa quả. Hỏi: Chiều cô ấy đi đâu?"),
    (False, ["星期二 [xīngqī'èr]", "星期三 [xīngqīsān]", "星期五 [xīngqīwǔ]"], "B",
     "明天 是 二 月 二十五 日，星期三。\n问：明天 是 星期 几？",
     "Míngtiān shì èr yuè èrshíwǔ rì, xīngqīsān.\n_ Míngtiān shì xīngqī jǐ?", "Mai là 25/2, thứ Tư. Hỏi: Mai là thứ mấy?"),
    (False, ["开 车 [kāi chē]", "做 饭 [zuò fàn]", "说 汉语 [shuō Hànyǔ]"], "C",
     "我 会 说 汉语，我 能 写 一些 汉字。\n问：他 会 什么？",
     "Wǒ huì shuō Hànyǔ, wǒ néng xiě yìxiē Hànzì.\n_ Tā huì shénme?", "Tôi biết nói tiếng Trung, viết được một ít chữ Hán. Hỏi: Anh ấy biết gì?"),
    (False, ["老师 [lǎoshī]", "妈妈 [māma]", "朋友 [péngyou]"], "A",
     "下 个 月，我 和 王 老师 去 北京。\n问：他 和 谁 去 北京？",
     "Xià ge yuè, wǒ hé Wáng lǎoshī qù Běijīng.\n_ Tā hé shéi qù Běijīng?", "Tháng sau tôi cùng thầy Vương đi Bắc Kinh. Hỏi: Anh ấy đi cùng ai?"),
    (False, ["4", "7", "10"], "A",
     "我 有 一 个 女儿，今年 四 岁 了。\n问：女儿 几 岁 了？",
     "Wǒ yǒu yí ge nǚ'ér, jīnnián sì suì le.\n_ Nǚ'ér jǐ suì le?", "Tôi có một con gái, năm nay 4 tuổi. Hỏi: Con gái mấy tuổi?"),
    (False, ["很 好 [hěn hǎo]", "很 热 [hěn rè]", "很 冷 [hěn lěng]"], "C",
     "昨天 下 雨 了，很 冷。\n问：昨天 天气 怎么样？",
     "Zuótiān xià yǔ le, hěn lěng.\n_ Zuótiān tiānqì zěnmeyàng?", "Hôm qua trời mưa, rất lạnh. Hỏi: Thời tiết hôm qua thế nào?"),
]

# ---------------------------------------------------------------- 二、阅读
# Phần 1 (câu 21–25): hình + từ → đúng/sai
R1 = [  # (ví dụ?, hình, từ, pinyin, đúng?, nghĩa)
    (True, 31, "电视", "diànshì", False, "tivi"),
    (True, 32, "飞机", "fēijī", True, "máy bay"),
    (False, 33, "猫", "māo", False, "con mèo"),
    (False, 34, "衣服", "yīfu", True, "quần áo"),
    (False, 35, "水果", "shuǐguǒ", True, "hoa quả"),
    (False, 36, "坐", "zuò", True, "ngồi"),
    (False, 37, "米饭", "mǐfàn", False, "cơm"),
]
# Phần 2 (câu 26–30): 6 hình A–F, đọc câu → ghép
R2_PICS = [38, 39, 40, 41, 42, 43]
R2 = [  # (ví dụ?, đáp án, câu, pinyin, dịch)
    (True, "E", "我 很 喜欢 这 本 书。", "Wǒ hěn xǐhuan zhè běn shū.", "Tôi rất thích quyển sách này."),
    (False, "F", "他 在 睡觉 呢。", "Tā zài shuìjiào ne.", "Anh ấy đang ngủ."),
    (False, "C", "她 明天 坐 火车 去。", "Tā míngtiān zuò huǒchē qù.", "Ngày mai cô ấy đi tàu hỏa."),
    (False, "D", "他 在 医院 工作，是 个 医生。", "Tā zài yīyuàn gōngzuò, shì ge yīshēng.", "Anh ấy làm ở bệnh viện, là bác sĩ."),
    (False, "B", "我 想 喝 一 杯 茶。", "Wǒ xiǎng hē yì bēi chá.", "Tôi muốn uống một tách trà."),
    (False, "A", "他们 是 同学。", "Tāmen shì tóngxué.", "Họ là bạn cùng lớp."),
]
# Phần 3 (câu 31–35): câu hỏi → ghép câu trả lời A–F
R3_OPTIONS = ["中国人。 [Zhōngguórén.]", "7 点 了。 [_ diǎn le.]", "苹果。 [Píngguǒ.]",
              "20 块。 [_ kuài.]", "坐 出租车。 [Zuò chūzūchē.]", "好 的， 谢谢！ [Hǎo de, xièxie!]"]
R3 = [
    (True, "F", "你 喝 水 吗？", "Nǐ hē shuǐ ma?", "Bạn uống nước không? – Vâng, cảm ơn!"),
    (False, "E", "你 怎么 去 那个 饭店？", "Nǐ zěnme qù nàge fàndiàn?", "Bạn đến khách sạn đó bằng cách nào? – Đi taxi."),
    (False, "B", "现在 几 点 了？", "Xiànzài jǐ diǎn le?", "Bây giờ mấy giờ rồi? – 7 giờ rồi."),
    (False, "C", "你 爱 吃 什么 水果？", "Nǐ ài chī shénme shuǐguǒ?", "Bạn thích ăn hoa quả gì? – Táo."),
    (False, "D", "这个 小 杯子 多少 钱？", "Zhège xiǎo bēizi duōshao qián?", "Cái cốc nhỏ này bao nhiêu tiền? – 20 tệ."),
    (False, "A", "你 是 哪 国 人？", "Nǐ shì nǎ guó rén?", "Bạn là người nước nào? – Người Trung Quốc."),
]
# Phần 4 (câu 36–40): chọn từ A–F điền chỗ trống
R4_OPTIONS = ["家 [jiā]", "火车站 [huǒchēzhàn]", "对不起 [duìbuqǐ]", "名字 [míngzi]", "看见 [kànjiàn]", "学习 [xuéxí]"]
R4 = [
    (True, "D", "你 叫 什么（　）？", "Nǐ jiào shénme", "Bạn tên là gì?"),
    (False, "F", "她 上午 在 学校（　）。", "Tā shàngwǔ zài xuéxiào", "Buổi sáng cô ấy học ở trường."),
    (False, "B", "我 7 点 30 分 去（　），10 点 前 回来。", "Wǒ _ diǎn _ fēn qù _ diǎn qián huílai.",
     "Tôi 7 giờ 30 đi ga tàu, trước 10 giờ quay về."),
    (False, "A", "喂，张 先生 在（　） 吗？", "Wéi, Zhāng xiānsheng zài ma?", "Alô, ông Trương có ở nhà không?"),
    (False, "C", "女：（　），我 今天 不 能 和 你 去 看 医生 了。\n男：没 关系。",
     "_ _ wǒ jīntiān bù néng hé nǐ qù kàn yīshēng le.\n_ Méi guānxi.",
     "Nữ: Xin lỗi, hôm nay em không thể cùng anh đi khám bác sĩ. – Nam: Không sao."),
    (False, "E", "男：你（　） 爸爸 的 衣服 了 吗？\n女：在 桌子 后面。",
     "_ Nǐ bàba de yīfu le ma?\n_ Zài zhuōzi hòumian.",
     "Nam: Em có thấy quần áo của bố không? – Nữ: Ở sau cái bàn."),
]


def base(skill: str, dang: str, **extra) -> dict:
    return {"dang": dang, "cap_do_id": 0, "ky_nang": skill, "dung_thi_thu": True, "dung_on_luyen": True, **extra}


def build() -> list[tuple[int, list[tuple[dict, bool]] | dict, bool]]:
    """Trả [(phần, câu_hoặc_ngữ_liệu, là_ngữ_liệu)] theo thứ tự đề."""
    plan = []
    for ex, pic, ok, said, py, vi in L1:
        plan.append((1, base("nghe", "dung_sai", tep_hinh=img(pic), loi_nghe=z(said), pinyin=py, dich_nghia=vi, phuong_an=tf(ok)), ex))
    for ex, ps, ans, said, py, vi in L2:
        plan.append((2, base("nghe", "chon_mot", loi_nghe=z(said), pinyin=py, dich_nghia=vi, phuong_an=pics(ps, LETTER[ans] - 1)), ex))
    plan.append((3, {"group": base("nghe", "ngu_lieu", phuong_an=pics(L3_PICS)),
                     "children": [({"dang": "chon_bo_chung", "loi_nghe": z(said), "pinyin": py, "dich_nghia": vi,
                                    "dap_an_thu_tu": LETTER[ans]}, ex) for ex, ans, said, py, vi in L3]}, None))
    for ex, opts, ans, said, py, vi in L4:
        plan.append((4, base("nghe", "chon_mot", loi_nghe=z(said), pinyin=py, dich_nghia=vi, phuong_an=words(opts, LETTER[ans] - 1)), ex))
    for ex, pic, word, py, ok, vi in R1:
        plan.append((5, base("doc", "dung_sai", tep_hinh=img(pic), noi_dung=word, pinyin=py, dich_nghia=vi, phuong_an=tf(ok)), ex))
    for part, opts, rows in ((6, None, R2), (7, R3_OPTIONS, R3), (8, R4_OPTIONS, R4)):
        shared = pics(R2_PICS) if opts is None else words(opts)
        plan.append((part, {"group": base("doc", "ngu_lieu", phuong_an=shared),
                            "children": [({"dang": "chon_bo_chung", "noi_dung": z(s), "pinyin": py, "dich_nghia": vi,
                                           "dap_an_thu_tu": LETTER[ans]}, ex) for ex, ans, s, py, vi in rows]}, None))
    return plan


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: python scripts/seed_hsk1_h10000.py <email Giảng viên>")
        return 1
    db = SessionLocal()
    try:
        lecturer = db.execute(text("SELECT id FROM nguoi_dung WHERE email = :e AND vai_tro_id = 3"),
                              {"e": sys.argv[1].strip().lower()}).scalar_one_or_none()
        if lecturer is None:
            print("✗ Không tìm thấy tài khoản Giảng viên với email này")
            return 1
        level = db.execute(text("SELECT id FROM cap_do WHERE ma = 'HSK1'")).scalar_one_or_none()
        if level is None:
            print("✗ Chưa có cấp HSK1 trong bảng cap_do")
            return 1
        if db.execute(text("SELECT 1 FROM bo_de WHERE ma_de = :m"), {"m": CODE}).first():
            print(f"✗ Đề {CODE} đã có, không nạp lại")
            return 1
        db.rollback()

        items: list[ExamItemIn] = []
        for part, entry, example in build():
            if isinstance(entry, dict) and "group" in entry:
                payload = {**entry["group"], "cap_do_id": level,
                           "cau_con": [child for child, _ in entry["children"]]}
                qid = create_question(db, QuestionIn(**payload), lecturer)
                publish_question(db, qid)
                child_ids = [r[0] for r in db.execute(text("SELECT id FROM cau_hoi WHERE cau_cha_id = :p ORDER BY id"), {"p": qid}).all()]
                for cid, (_, is_example) in zip(child_ids, entry["children"]):
                    items.append(ExamItemIn(cau_hoi_id=cid, phan=part, la_cau_vi_du=is_example))
            else:
                qid = create_question(db, QuestionIn(**{**entry, "cap_do_id": level}), lecturer)
                publish_question(db, qid)
                items.append(ExamItemIn(cau_hoi_id=qid, phan=part, la_cau_vi_du=example))

        exam_id = exam_service.create_exam(db, ExamInfoIn(
            cap_do_id=level, ten="HSK 1 – Đề 1", ma_de=CODE, thoi_luong_phut=40,
            nguon="Hanban/孔子学院总部 – HSK（一级）样卷", tep_audio_chung=AUDIO,
        ), lecturer)
        exam_service.set_exam_items(db, exam_id, items)
        exam_service.publish_exam(db, exam_id)
        scored = sum(1 for i in items if not i.la_cau_vi_du)
        print(f"→ Đã nạp đề {CODE}: {scored} câu tính điểm, {len(items) - scored} câu ví dụ. Đề đã đăng.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
