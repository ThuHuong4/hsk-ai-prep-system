"""Nạp 3 đề thi thử HSK 1 gốc (H10901 – Đề 2, H10902 – Đề 3, H11003 – Đề 4) vào CSDL Xianglingo.

Nguồn: 国家汉办/孔子学院总部 – 新汉语水平考试 HSK（一级）H10901, H10902, H11003 (từ bộ tệp PDF + MP3 gốc).
Hình nằm tại uploads/exams/hsk1_<mã>/img/000..043.jpg; băng nghe tại uploads/exams/hsk1_<mã>/listening.mp3.
An toàn khi chạy lại nhiều lần (bỏ qua đề đã tồn tại theo ma_de).
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemIn
from app.modules.exam_authoring.services import exam_service
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

UPLOADS = Path(__file__).resolve().parents[1] / "uploads"
LETTER = {c: i + 1 for i, c in enumerate("ABCDEF")}


def tf(correct: bool) -> list[dict]:
    return [{"noi_dung": "Đúng", "la_dap_an_dung": correct}, {"noi_dung": "Sai", "la_dap_an_dung": not correct}]


def words(items: list[str], answer: int | None = None) -> list[dict]:
    return [{"noi_dung": w, "la_dap_an_dung": answer == i} for i, w in enumerate(items)]


def z(value: str) -> str:
    return re.sub(r"([，：])(?=\S)", r"\1 ", value)


EXAMS_HSK1 = [
    # ==========================================================================
    # HSK 1 – Đề 2 (H10901)
    # ==========================================================================
    {
        "code": "H10901",
        "ten": "HSK 1 – Đề 2",
        "slug": "hsk1_h10901",
        "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（一级）H10901",
        "L1": [
            (True, 0, True, "很 高兴", "hěn gāoxìng", "Rất vui."),
            (True, 1, False, "看 电影", "kàn diànyǐng", "Xem phim."),
            (False, 2, True, "打 电话", "dǎ diànhuà", "Gọi điện thoại."),
            (False, 3, False, "我 和 儿子", "wǒ hé érzi", "Tôi và con trai."),
            (False, 4, False, "开 车", "kāi chē", "Lái xe ô tô."),
            (False, 5, False, "吃 米饭", "chī mǐfàn", "Ăn cơm."),
            (False, 6, True, "下 雨 了", "xià yǔ le", "Trời mưa rồi."),
        ],
        "L2": [
            (True, [7, 8, 9], "A", "这 是 我 的 书。", "Zhè shì wǒ de shū.", "Đây là sách của tôi."),
            (False, [10, 11, 12], "A", "今天 天气 很 冷。", "Jīntiān tiānqì hěn lěng.", "Hôm nay thời tiết rất lạnh."),
            (False, [13, 14, 15], "A", "现在 是 十 点 十 分。", "Xiànzài shì shí diǎn shí fēn.", "Bây giờ là 10 giờ 10 phút."),
            (False, [16, 17, 18], "C", "她 后面 有 几 个 人。", "Tā hòumiàn yǒu jǐ ge rén.", "Phía sau cô ấy có mấy người."),
            (False, [19, 20, 21], "A", "我 今年 12 岁 了。", "Wǒ jīnnián _ suì le.", "Năm nay tôi 12 tuổi rồi."),
            (False, [22, 23, 24], "C", "他 下 个 月 去 中国。", "Tā xià ge yuè qù Zhōngguó.", "Tháng sau anh ấy đi Trung Quốc."),
        ],
        "L3": [
            (True, "C", "女：你 好！\n男：你 好！ 很 高兴 认识 你。", "_ Nǐ hǎo!\n_ Nǐ hǎo! Hěn gāoxìng rènshi nǐ.", "Nữ: Chào anh! – Nam: Chào chị! Rất vui được làm quen."),
            (False, "D", "男：你 看见 我 的 小 猫 了 吗？\n女：在 那儿，在 椅子 上。", "_ Nǐ kànjiàn wǒ de xiǎo māo le ma?\n_ Zài nàr, zài yǐzi shàng.", "Bạn thấy chú mèo nhỏ của tôi không? – Ở đằng kia, trên ghế."),
            (False, "B", "女：我们 中午 去 买，好 吗？\n男：你 看，我 没 钱 了。", "_ Wǒmen zhōngwǔ qù mǎi, hǎo ma?\n_ Nǐ kàn, wǒ méi qián le.", "Trưa nay mình đi mua nhé? – Nhìn này, tôi hết tiền rồi."),
            (False, "A", "男：你 住 在 哪儿？\n女：我 和 妈妈 都 住 在 一零二。", "_ Nǐ zhù zài nǎr?\n_ Wǒ hé māma dōu zhù zài yīlíng'èr.", "Bạn sống ở đâu? – Tôi và mẹ đều ở phòng 102."),
            (False, "E", "女：这个 汉字 怎么 读？\n男：对不起，我 不 会。", "_ Zhège Hànzì zěnme dú?\n_ Duìbuqǐ, wǒ bú huì.", "Chữ Hán này đọc thế nào? – Xin lỗi, tôi không biết."),
            (False, "F", "男：谢谢 你们！\n女：不 客气。 再见。", "_ Xièxie nǐmen!\n_ Bú kèqi. Zàijiàn.", "Cảm ơn các bạn! – Đừng khách sáo. Tạm biệt."),
        ],
        "L4": [
            (True, ["商店 [shāngdiàn]", "医院 [yīyuàn]", "学校 [xuéxiào]"], "A",
             "下午 我 去 商店，我 想 买 一些 水果。\n问：她 下午 去 哪里？",
             "Xiàwǔ wǒ qù shāngdiàn, wǒ xiǎng mǎi yìxiē shuǐguǒ.\n_ Tā xiàwǔ qù nǎlǐ?", "Chiều tôi đi cửa hàng mua hoa quả. Hỏi: Chiều cô ấy đi đâu?"),
            (False, ["他 的 [tā de]", "我 的 [wǒ de]", "同学 的 [tóngxué de]"], "B",
             "我 的 电脑 在 他 的 桌子 上。\n问：那 是 谁 的 电脑？",
             "Wǒ de diànnǎo zài tā de zhuōzi shàng.\n_ Nà shì shéi de diànnǎo?", "Máy tính của tôi ở trên bàn anh ấy. Hỏi: Đó là máy tính của ai?"),
            (False, ["星期三 [xīngqīsān]", "星期五 [xīngqīwǔ]", "星期六 [xīngqīliù]"], "B",
             "今天 星期四，我们 明天 去 看 电影。\n问：我们 什么 时候 去 看 电影？",
             "Jīntiān xīngqīsì, wǒmen míngtiān qù kàn diànyǐng.\n_ Wǒmen shénme shíhou qù kàn diànyǐng?", "Hôm nay thứ Tư, mai chúng tôi đi xem phim. Hỏi: Khi nào đi xem phim?"),
            (False, ["5", "15", "50"], "C",
             "他 是 老师，他 有 50 个 学生。\n问：他 有 多少 个 学生？",
             "Tā shì lǎoshī, tā yǒu _ ge xuésheng.\n_ Tā yǒu duōshao ge xuésheng?", "Anh ấy là giáo viên, có 50 học sinh. Hỏi: Anh ấy có bao nhiêu học sinh?"),
            (False, ["茶 [chá]", "苹果 [píngguǒ]", "杯子 [bēizi]"], "C",
             "小姐，你 好，你 这儿 有 杯子 吗？\n问：他 想 买 什么？",
             "Xiǎojiě, nǐ hǎo, nǐ zhèr yǒu bēizi ma?\n_ Tā xiǎng mǎi shénme?", "Chào cô, chỗ cô có bán cốc không? Hỏi: Anh ấy muốn mua gì?"),
            (False, ["爱 学习 [ài xuéxí]", "很 漂亮 [hěn piàoliang]", "想 回 家 [xiǎng huí jiā]"], "B",
             "这 是 你 的 朋友 吗？ 很 漂亮。\n问：朋友 怎么样？",
             "Zhè shì nǐ de péngyou ma? Hěn piàoliang.\n_ Péngyou zěnmeyàng?", "Đây là bạn của bạn à? Rất xinh đẹp. Hỏi: Người bạn thế nào?"),
        ],
        "R1": [
            (True, 31, "电视", "diànshì", False, "tivi"),
            (True, 32, "飞机", "fēijī", True, "máy bay"),
            (False, 33, "写", "xiě", True, "viết"),
            (False, 34, "听", "tīng", True, "nghe"),
            (False, 35, "菜", "cài", False, "món ăn / rau"),
            (False, 36, "他", "tā", False, "anh ấy"),
            (False, 37, "狗", "gǒu", True, "con chó"),
        ],
        "R2": [
            (True, "E", "我 很 喜欢 这 本 书。", "Wǒ hěn xǐhuan zhè běn shū.", "Tôi rất thích quyển sách này."),
            (False, "D", "你 好，我 能 吃 一 块儿 吗？", "Nǐ hǎo, wǒ néng chī yí kuàir ma?", "Xin chào, tôi ăn một miếng được không?"),
            (False, "F", "她们 在 买 衣服 呢。", "Tāmen zài mǎi yīfu ne.", "Họ đang mua quần áo."),
            (False, "C", "天气 太 热 了，多 吃 些 水果。", "Tiānqì tài rè le, duō chī xiē shuǐguǒ.", "Trời nóng quá, ăn nhiều hoa quả một chút."),
            (False, "A", "来，我们 看看 里面 是 什么 东西。", "Lái, wǒmen kànkan lǐmiàn shì shénme dōngxi.", "Nào, chúng ta xem bên trong là thứ gì."),
            (False, "B", "喂，你 睡觉 了 吗？", "Wéi, nǐ shuìjiào le ma?", "Alô, bạn đã ngủ chưa?"),
        ],
        "R3_OPTIONS": [
            "医院。 [Yīyuàn.]",
            "下 雨 了。 [Xià yǔ le.]",
            "我 不 认识 她。 [Wǒ bú rènshi tā.]",
            "7 岁。 [_ suì.]",
            "下 个 月。 [Xià ge yuè.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            (True, "F", "你 喝 水 吗？", "Nǐ hē shuǐ ma?", "Bạn uống nước không? – Vâng, cảm ơn!"),
            (False, "C", "那个 人 是 谁？", "Nàge rén shì shéi?", "Người kia là ai? – Tôi không quen cô ấy."),
            (False, "D", "他 女儿 多 大 了？", "Tā nǚ'ér duō dà le?", "Con gái anh ấy bao nhiêu tuổi rồi? – 7 tuổi."),
            (False, "A", "你 的 同学 在 哪儿 工作？", "Nǐ de tóngxué zài nǎr gōngzuò?", "Bạn học của bạn làm việc ở đâu? – Ở bệnh viện."),
            (False, "B", "昨天 上午 天气 怎么样？", "Zuótiān shàngwǔ tiānqì zěnmeyàng?", "Sáng hôm qua thời tiết thế nào? – Trời mưa."),
            (False, "E", "爸爸 什么 时候 来 北京 呢？", "Bàba shénme shíhou lái Běijīng ne?", "Khi nào bố đến Bắc Kinh vậy? – Tháng sau."),
        ],
        "R4_OPTIONS": [
            "坐 [zuò]",
            "前面 [qiánmiàn]",
            "没 关系 [méi guānxi]",
            "名字 [míngzi]",
            "汉语 [Hànyǔ]",
            "月 [yuè]",
        ],
        "R4": [
            (True, "D", "你 叫 什么 （　）？", "Nǐ jiào shénme _", "Bạn tên là gì?"),
            (False, "F", "昨天 是 8 （　） 19 日。", "Zuótiān shì _ _ _ rì.", "Hôm qua là ngày 19 tháng 8."),
            (False, "B", "那个 饭馆儿 在 火车站 （　）。", "Nàge fànguǎnr zài huǒchēzhàn _", "Quán ăn đó ở phía trước ga tàu hỏa."),
            (False, "E", "你 会 说 （　） 吗？", "Nǐ huì shuō _ ma?", "Bạn biết nói tiếng Hán không?"),
            (False, "A", "男：你 好！ 王 先生 在 吗？\n女：在，请 （　），我 去 叫 他。",
             "_ Nǐ hǎo! Wáng xiānsheng zài ma?\n_ Zài, qǐng _ wǒ qù jiào tā.",
             "Xin chào! Ông Vương có ở đây không? – Có, mời ngồi, tôi đi gọi ông ấy."),
            (False, "C", "女：对不起，我 不 会 做 饭。\n男：（　），我 会。",
             "_ Duìbuqǐ, wǒ bú huì zuò fàn.\n_ _ wǒ huì.",
             "Xin lỗi, em không biết nấu cơm. – Không sao, anh biết nấu."),
        ],
    },

    # ==========================================================================
    # HSK 1 – Đề 3 (H10902)
    # ==========================================================================
    {
        "code": "H10902",
        "ten": "HSK 1 – Đề 3",
        "slug": "hsk1_h10902",
        "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（一级）H10902",
        "L1": [
            (True, 0, True, "很 高兴", "hěn gāoxìng", "Rất vui."),
            (True, 1, False, "看 电影", "kàn diànyǐng", "Xem phim."),
            (False, 2, False, "她 的 猫", "tā de māo", "Con mèo của cô ấy."),
            (False, 3, False, "吃 东西", "chī dōngxi", "Ăn đồ ăn."),
            (False, 4, False, "在 商店 里", "zài shāngdiàn lǐ", "Ở trong cửa hàng."),
            (False, 5, True, "再见", "zàijiàn", "Tạm biệt."),
            (False, 6, True, "请 喝 茶", "qǐng hē chá", "Mời uống trà."),
        ],
        "L2": [
            (True, [7, 8, 9], "A", "这 是 我 的 书。", "Zhè shì wǒ de shū.", "Đây là sách của tôi."),
            (False, [10, 11, 12], "B", "儿子 爱 吃 米饭。", "Érzi ài chī mǐfàn.", "Con trai thích ăn cơm."),
            (False, [13, 14, 15], "A", "我 喜欢 这个 电脑。", "Wǒ xǐhuan zhège diànnǎo.", "Tôi thích chiếc máy tính này."),
            (False, [16, 17, 18], "C", "我 看见 她 买 衣服 了。", "Wǒ kànjiàn tā mǎi yīfu le.", "Tôi thấy cô ấy mua quần áo rồi."),
            (False, [19, 20, 21], "A", "苹果 在 桌子 上。", "Píngguǒ zài zhuōzi shàng.", "Táo ở trên bàn."),
            (False, [22, 23, 24], "B", "北京 一 年 中 有 三 个 月 很 冷。", "Běijīng yì nián zhōng yǒu sān ge yuè hěn lěng.", "Bắc Kinh một năm có 3 tháng rất lạnh."),
        ],
        "L3": [
            (True, "C", "女：你 好！\n男：你 好！ 很 高兴 认识 你。", "_ Nǐ hǎo!\n_ Nǐ hǎo! Hěn gāoxìng rènshi nǐ.", "Chào anh! – Chào cô! Rất vui được làm quen."),
            (False, "E", "男：上午 去 医院 看 同学 的 时候，你 没 买 些 水果？\n女：我 买 了 不少。",
             "_ Shàngwǔ qù yīyuàn kàn tóngxué de shíhou, nǐ méi mǎi xiē shuǐguǒ?\n_ Wǒ mǎi le bù shǎo.",
             "Sáng nay tới viện thăm bạn học, bạn không mua ít hoa quả à? – Tôi mua khá nhiều rồi."),
            (False, "F", "女：你 是 哪 年 来 中国 的？\n男：我？ 今年，2009 年。",
             "_ Nǐ shì nǎ nián lái Zhōngguó de?\n_ Wǒ? Jīnnián, _ nián.",
             "Bạn đến Trung Quốc năm nào? – Tôi á? Năm nay, năm 2009."),
            (False, "D", "男：你 的 大 狗 叫 什么 名字？\n女：叫 多多。 多多 是 我 的 好 朋友。",
             "_ Nǐ de dà gǒu jiào shénme míngzi?\n_ Jiào Duōduo. Duōduo shì wǒ de hǎo péngyou.",
             "Chú chó lớn của bạn tên gì? – Tên Đa Đa. Đa Đa là bạn tốt của tôi."),
            (False, "B", "女：李 老师 的 女儿 今年 二十 岁 了？\n男：是。 她 很 漂亮。",
             "_ Lǐ lǎoshī de nǚ'ér jīnnián èrshí suì le?\n_ Shì. Tā hěn piàoliang.",
             "Con gái thầy Lý năm nay 20 tuổi rồi à? – Đúng vậy. Cô ấy rất xinh."),
            (False, "A", "男：现在 几 点 了？\n女：十 点 十 分。",
             "_ Xiànzài jǐ diǎn le?\n_ Shí diǎn shí fēn.",
             "Bây giờ mấy giờ rồi? – 10 giờ 10 phút."),
        ],
        "L4": [
            (True, ["商店 [shāngdiàn]", "医院 [yīyuàn]", "学校 [xuéxiào]"], "A",
             "下午 我 去 商店，我 想 买 一些 水果。\n问：她 下午 去 哪里？",
             "Xiàwǔ wǒ qù shāngdiàn, wǒ xiǎng mǎi yìxiē shuǐguǒ.\n_ Tā xiàwǔ qù nǎlǐ?", "Chiều tôi đi cửa hàng mua hoa quả. Hỏi: Chiều cô ấy đi đâu?"),
            (False, ["7 块 [_ kuài]", "8 块 [_ kuài]", "18 块 [_ kuài]"], "C",
             "你 好，这个 杯子 十八 块 钱。\n问：那个 杯子 多少 钱？",
             "Nǐ hǎo, zhège bēizi shíbā kuài qián.\n_ Nàge bēizi duōshao qián?", "Xin chào, chiếc cốc này 18 tệ. Hỏi: Chiếc cốc giá bao nhiêu?"),
            (False, ["饭店 [fàndiàn]", "家 里 [jiā li]", "朋友 家 [péngyou jiā]"], "A",
             "中午 我 不 回 家 吃 饭 了，和 朋友 在 饭店 吃。\n问：我 在 哪儿 吃 午饭？",
             "Zhōngwǔ wǒ bù huí jiā chī fàn le, hé péngyou zài fàndiàn chī.\n_ Wǒ zài nǎr chī wǔfàn?", "Trưa tôi không về nhà ăn, ăn ở nhà hàng với bạn. Hỏi: Tôi ăn trưa ở đâu?"),
            (False, ["写 字 [xiě zì]", "看 电视 [kàn diànshì]", "打 电话 [dǎ diànhuà]"], "C",
             "喂？ 是 王 先生 吗？\n问：他 在 做 什么？",
             "Wéi? Shì Wáng xiānsheng ma?\n_ Tā zài zuò shénme?", "Alô? Phải ông Vương không ạ? Hỏi: Anh ấy đang làm gì?"),
            (False, ["星期五 [xīngqīwǔ]", "星期六 [xīngqīliù]", "星期日 [xīngqīrì]"], "C",
             "明天 星期一，我 去 学校。\n问：今天 星期几？",
             "Míngtiān xīngqīyī, wǒ qù xuéxiào.\n_ Jīntiān xīngqījǐ?", "Ngày mai thứ Hai tôi đi học. Hỏi: Hôm nay là thứ mấy?"),
            (False, ["开 车 [kāi chē]", "坐 飞机 [zuò fēijī]", "坐 火车 [zuò huǒchē]"], "B",
             "他 不 想 坐 火车，我们 坐 飞机 去。\n问：他们 怎么 去？",
             "Tā bù xiǎng zuò huǒchē, wǒmen zuò fēijī qù.\n_ Tāmen zěnme qù?", "Anh ấy không muốn đi tàu hỏa, chúng tôi đi máy bay. Hỏi: Họ đi bằng gì?"),
        ],
        "R1": [
            (True, 31, "电视", "diànshì", False, "tivi"),
            (True, 32, "飞机", "fēijī", True, "máy bay"),
            (False, 33, "水", "shuǐ", False, "nước"),
            (False, 34, "读", "dú", True, "đọc"),
            (False, 35, "工作", "gōngzuò", False, "làm việc"),
            (False, 36, "睡觉", "shuìjiào", True, "ngủ"),
            (False, 37, "椅子", "yǐzi", True, "cái ghế"),
        ],
        "R2": [
            (True, "E", "我 很 喜欢 这 本 书。", "Wǒ hěn xǐhuan zhè běn shū.", "Tôi rất thích quyển sách này."),
            (False, "A", "这些 都 是 张 小姐 的。", "Zhèxiē dōu shì Zhāng xiǎojiě de.", "Chỗ này đều là của cô Trương."),
            (False, "B", "没 关系，不 会 做 没 关系。", "Méi guānxi, bú huì zuò méi guānxi.", "Không sao đâu, không biết làm cũng không sao."),
            (False, "C", "10 月 前 我 回来，再见。", "_ yuè qián wǒ huílai, zàijiàn.", "Trước tháng 10 tôi sẽ về, tạm biệt."),
            (False, "D", "对不起，今天 天气 太 热 了。", "Duìbuqǐ, jīntiān tiānqì tài rè le.", "Xin lỗi, thời tiết hôm nay nóng quá."),
            (False, "F", "妈妈，我 不 爱 吃 这个 菜。", "Māma, wǒ bú ài chī zhège cài.", "Mẹ ơi, con không thích ăn món này."),
        ],
        "R3_OPTIONS": [
            "都 很 好。 [Dōu hěn hǎo.]",
            "昨天 下午。 [Zuótiān xiàwǔ.]",
            "那儿。 [Nàr.]",
            "听 你 的。 [Tīng nǐ de.]",
            "后面 的 人。 [Hòumian de rén.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            (True, "F", "你 喝 水 吗？", "Nǐ hē shuǐ ma?", "Bạn uống nước không? – Vâng, cảm ơn!"),
            (False, "C", "医生！ 医生 在 哪儿？", "Yīshēng! Yīshēng zài nǎr?", "Bác sĩ! Bác sĩ ở đâu? – Ở đằng kia."),
            (False, "E", "谁 在 说话？", "Shéi zài shuōhuà?", "Ai đang nói chuyện vậy? – Người ở phía sau."),
            (False, "B", "李 先生 是 什么 时候 来 的？", "Lǐ xiānsheng shì shénme shíhou lái de?", "Ông Lý đến từ lúc nào? – Chiều hôm qua."),
            (False, "D", "我们 去 下面 吃？", "Wǒmen qù xiàmiàn chī?", "Chúng ta xuống dưới ăn nhé? – Nghe theo bạn đấy."),
            (False, "A", "那 几 本 书 怎么样？", "Nà jǐ běn shū zěnmeyàng?", "Mấy quyển sách đó thế nào? – Đều rất hay."),
        ],
        "R4_OPTIONS": [
            "能 [néng]",
            "住 [zhù]",
            "认识 [rènshi]",
            "名字 [míngzi]",
            "坐 [zuò]",
            "谢谢 [xièxie]",
        ],
        "R4": [
            (True, "D", "你 叫 什么 （　）？", "Nǐ jiào shénme _", "Bạn tên là gì?"),
            (False, "B", "我 在 中国 （　） 了 4 年 了。", "Wǒ zài Zhōngguó _ le _ nián le.", "Tôi sống ở Trung Quốc đã 4 năm rồi."),
            (False, "E", "爸爸，下 雨 了，我们 怎么 回 家？ （　） 出租车 吗？",
             "Bàba, xià yǔ le, wǒmen zěnme huí jiā? _ chūzūchē ma?",
             "Bố ơi, trời mưa rồi, mình về nhà thế nào? Đi taxi nhé?"),
            (False, "A", "（　） 来 这儿 学习 汉语，我 很 高兴。", "_ lái zhèr xuéxí Hànyǔ, wǒ hěn gāoxìng.", "Có thể đến đây học tiếng Hán, tôi rất vui."),
            (False, "F", "女：（　） 你 请 我 看 电影。\n男：不 客气。",
             "_ _ nǐ qǐng wǒ kàn diànyǐng.\n_ Bú kèqi.",
             "Cảm ơn bạn đã mời tôi xem phim. – Đừng khách sáo."),
            (False, "C", "男：你 （　） 他？ 他 是 谁？\n女：他 是 我 的 学生。",
             "_ Nǐ _ tā? Tā shì shéi?\n_ Tā shì wǒ de xuésheng.",
             "Bạn quen cậu ấy à? Cậu ấy là ai? – Cậu ấy là học sinh của tôi."),
        ],
    },

    # ==========================================================================
    # HSK 1 – Đề 4 (H11003)
    # ==========================================================================
    {
        "code": "H11003",
        "ten": "HSK 1 – Đề 4",
        "slug": "hsk1_h11003",
        "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（一级）H11003",
        "L1": [
            (True, 0, True, "很 高兴", "hěn gāoxìng", "Rất vui."),
            (True, 1, False, "看 电影", "kàn diànyǐng", "Xem phim."),
            (False, 2, False, "太 热 了", "tài rè le", "Nóng quá."),
            (False, 3, True, "三 个 杯子", "sān ge bēizi", "Ba chiếc cốc."),
            (False, 4, True, "读 书", "dú shū", "Đọc sách."),
            (False, 5, False, "吃 菜", "chī cài", "Ăn thức ăn."),
            (False, 6, False, "在 医院", "zài yīyuàn", "Ở bệnh viện."),
        ],
        "L2": [
            (True, [7, 8, 9], "A", "这 是 我 的 书。", "Zhè shì wǒ de shū.", "Đây là sách của tôi."),
            (False, [10, 11, 12], "C", "我 会 做 饭。", "Wǒ huì zuò fàn.", "Tôi biết nấu ăn."),
            (False, [13, 14, 15], "A", "你 好，这个 电视 多少 钱？", "Nǐ hǎo, zhège diànshì duōshao qián?", "Xin chào, chiếc tivi này giá bao nhiêu?"),
            (False, [16, 17, 18], "C", "他 妈妈 是 医生。", "Tā māma shì yīshēng.", "Mẹ anh ấy là bác sĩ."),
            (False, [19, 20, 21], "B", "我 今天 开 车 回 家。", "Wǒ jīntiān kāi chē huí jiā.", "Hôm nay tôi lái xe về nhà."),
            (False, [22, 23, 24], "C", "这个 衣服 太 小 了。", "Zhège yīfu tài xiǎo le.", "Chiếc áo này nhỏ quá."),
        ],
        "L3": [
            (True, "C", "女：你 好！\n男：你 好！ 很 高兴 认识 你。", "_ Nǐ hǎo!\n_ Nǐ hǎo! Hěn gāoxìng rènshi nǐ.", "Chào anh! – Chào cô! Rất vui được làm quen."),
            (False, "E", "男：这儿 怎么 了？\n女：这里 很 多 年 没 下 雨 了。",
             "_ Zhèr zěnme le?\n_ Zhèlǐ hěn duō nián méi xià yǔ le.",
             "Chỗ này bị sao vậy? – Nơi đây nhiều năm rồi không mưa."),
            (False, "F", "女：再见。\n男：好，星期日 火车站 见。",
             "_ Zàijiàn.\n_ Hǎo, xīngqīrì huǒchēzhàn jiàn.",
             "Tạm biệt. – Ừ, Chủ nhật gặp ở ga tàu hỏa nhé."),
            (False, "A", "男：这些 字 是 你 写 的？ 很 漂亮！\n女：谢谢 你！",
             "_ Zhèxiē zì shì nǐ xiě de? Hěn piàoliang!\n_ Xièxie nǐ!",
             "Mấy chữ này là bạn viết à? Đẹp lắm! – Cảm ơn bạn!"),
            (False, "B", "男：不 能 在 这儿 睡觉，去 里面 睡。\n女：五 分钟，我 睡 五 分钟。",
             "_ Bù néng zài zhèr shuìjiào, qù lǐmiàn shuì.\n_ Wǔ fēnzhōng, wǒ shuì wǔ fēnzhōng.",
             "Không ngủ ở đây được đâu, vào trong ngủ đi. – Năm phút thôi, tôi chợp mắt 5 phút."),
            (False, "D", "男：这 一 块 钱 不 是 你 的 吗？ 对不起。\n女：没 关系。",
             "_ Zhè yí kuài qián bú shì nǐ de ma? Duìbuqǐ.\n_ Méi guānxi.",
             "Đồng 1 tệ này không phải của bạn à? Xin lỗi nhé. – Không sao."),
        ],
        "L4": [
            (True, ["商店 [shāngdiàn]", "医院 [yīyuàn]", "学校 [xuéxiào]"], "A",
             "下午 我 去 商店，我 想 买 一些 水果。\n问：她 下午 去 哪里？",
             "Xiàwǔ wǒ qù shāngdiàn, wǒ xiǎng mǎi yìxiē shuǐguǒ.\n_ Tā xiàwǔ qù nǎlǐ?", "Chiều tôi đi cửa hàng mua hoa quả. Hỏi: Chiều cô ấy đi đâu?"),
            (False, ["狗 [gǒu]", "猫 [māo]", "猫 和 狗 [māo hé gǒu]"], "A",
             "我 喜欢 狗，不 太 喜欢 猫。\n问：他 喜欢 什么？",
             "Wǒ xǐhuan gǒu, bú tài xǐhuan māo.\n_ Tā xǐhuan shénme?", "Tôi thích chó, không thích mèo lắm. Hỏi: Anh ấy thích gì?"),
            (False, ["0", "6 年 [_ nián]", "7 年 [_ nián]"], "C",
             "小赵 在 那儿 工作 了 七 年，认识 很 多 朋友。\n问：小赵 在 那儿 工作 了 几 年？",
             "Xiǎo Zhào zài nàr gōngzuò le qī nián, rènshi hěn duō péngyou.\n_ Xiǎo Zhào zài nàr gōngzuò le jǐ nián?",
             "Tiểu Triệu làm việc ở đó 7 năm. Hỏi: Tiểu Triệu làm ở đó mấy năm?"),
            (False, ["桌子 上 [zhuōzi shang]", "椅子 上 [yǐzi shang]", "电脑 后面 [diànnǎo hòumiàn]"], "A",
             "你 的 那 本 书？ 在 桌子 上。\n问：那 本 书 在 哪儿？",
             "Nǐ de nà běn shū? Zài zhuōzi shàng.\n_ Nà běn shū zài nǎr?", "Quyển sách kia của bạn á? Ở trên bàn. Hỏi: Quyển sách ở đâu?"),
            (False, ["上午 [shàngwǔ]", "明天 [míngtiān]", "下 个 月 [xià ge yuè]"], "B",
             "下午 我 不 在 家，你 明天 来 好 吗？\n问：他 什么 时候 在 家？",
             "Xiàwǔ wǒ bú zài jiā, nǐ míngtiān lái hǎo ma?\n_ Tā shénme shíhou zài jiā?", "Chiều tôi không ở nhà, mai bạn tới nhé? Hỏi: Khi nào anh ấy ở nhà?"),
            (False, ["8 岁 [_ suì]", "20 岁 [_ suì]", "40 岁 [_ suì]"], "B",
             "他 儿子 今年 二十 岁，是 个 大学生。\n问：他 儿子 多 大 了？",
             "Tā érzi jīnnián èrshí suì, shì ge dàxuéshēng.\n_ Tā érzi duō dà le?", "Con trai ông ấy năm nay 20 tuổi, là sinh viên. Hỏi: Con trai ông ấy bao nhiêu tuổi?"),
        ],
        "R1": [
            (True, 31, "电视", "diànshì", False, "tivi"),
            (True, 32, "飞机", "fēijī", True, "máy bay"),
            (False, 33, "听", "tīng", False, "nghe"),
            (False, 34, "米饭", "mǐfàn", True, "cơm"),
            (False, 35, "高兴", "gāoxìng", True, "vui vẻ"),
            (False, 36, "九 点", "jiǔ diǎn", True, "9 giờ"),
            (False, 37, "学习", "xuéxí", False, "học tập"),
        ],
        "R2": [
            (True, "E", "我 很 喜欢 这 本 书。", "Wǒ hěn xǐhuan zhè běn shū.", "Tôi rất thích quyển sách này."),
            (False, "B", "李 老师 在 打 电话 呢。", "Lǐ lǎoshī zài dǎ diànhuà ne.", "Cô Lý đang gọi điện thoại."),
            (False, "A", "家 里 有 很 多 苹果。", "Jiā lǐ yǒu hěn duō píngguǒ.", "Trong nhà có rất nhiều táo."),
            (False, "F", "我们 去 前面 那个 饭馆儿 吃 饭，怎么样？", "Wǒmen qù qiánmiàn nàge fànguǎnr chī fàn, zěnmeyàng?", "Chúng mình đến quán ăn phía trước dùng bữa, thế nào?"),
            (False, "C", "我 和 女儿 都 爱 看 电影。", "Wǒ hé nǚ'ér dōu ài kàn diànyǐng.", "Tôi và con gái đều thích xem phim."),
            (False, "D", "不 客气，王 先生，请 坐。", "Bú kèqi, Wáng xiānsheng, qǐng zuò.", "Đừng khách sáo, ông Vương, mời ngồi."),
        ],
        "R3_OPTIONS": [
            "没。 [Méi.]",
            "学校 里。 [Xuéxiào lǐ.]",
            "会 说 一些。 [Huì shuō yìxiē.]",
            "这个。 [Zhège.]",
            "我 爸爸 妈妈。 [Wǒ bàba māma.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            (True, "F", "你 喝 水 吗？", "Nǐ hē shuǐ ma?", "Bạn uống nước không? – Vâng, cảm ơn!"),
            (False, "D", "哪个 是 你 的 同学？", "Nǎge shì nǐ de tóngxué?", "Người nào là bạn học của bạn? – Người này."),
            (False, "C", "你 汉语 怎么样？", "Nǐ Hànyǔ zěnmeyàng?", "Tiếng Hán của bạn thế nào? – Biết nói một chút."),
            (False, "A", "你 看见 张 小姐 了 吗？", "Nǐ kànjiàn Zhāng xiǎojiě le ma?", "Bạn có nhìn thấy cô Trương không? – Chưa."),
            (False, "E", "对不起，他们 是 谁？", "Duìbuqǐ, tāmen shì shéi?", "Xin lỗi, họ là ai vậy? – Bố mẹ của tôi."),
            (False, "B", "你 现在 住 在 哪儿？", "Nǐ xiànzài zhù zài nǎr?", "Hiện bạn sống ở đâu? – Ở trong trường."),
        ],
        "R4_OPTIONS": [
            "冷 [lěng]",
            "多少 [duōshao]",
            "写 [xiě]",
            "名字 [míngzi]",
            "茶 [chá]",
            "东西 [dōngxi]",
        ],
        "R4": [
            (True, "D", "你 叫 什么 （　）？", "Nǐ jiào shénme _", "Bạn tên là gì?"),
            (False, "E", "中国人 喜欢 喝 （　）。", "Zhōngguórén xǐhuan hē _", "Người Trung Quốc thích uống trà."),
            (False, "F", "喂，中午 你 买 什么 （　） 了？", "Wéi, zhōngwǔ nǐ mǎi shénme _ le?", "Alô, buổi trưa bạn đã mua đồ gì thế?"),
            (False, "C", "他 少 （　） 了 一 个 零。", "Tā shǎo _ le yí ge líng.", "Anh ấy viết thiếu một số không."),
            (False, "B", "女：你 开 出租车 （　） 年 了？\n男：十几 年 了。",
             "_ Nǐ kāi chūzūchē _ nián le?\n_ Shíjǐ nián le.",
             "Anh lái xe taxi bao nhiêu năm rồi? – Mười mấy năm rồi."),
            (False, "A", "男：北京 昨天 天气 怎么样？\n女：很 （　）。",
             "_ Běijīng zuótiān tiānqì zěnmeyàng?\n_ Hěn _",
             "Thời tiết Bắc Kinh hôm qua thế nào? – Rất lạnh."),
        ],
    },
]


def build_plan(cfg: dict) -> list[tuple[int, dict, bool | None]]:
    slug = cfg["slug"]
    img = lambda n: f"exams/{slug}/img/{n:03d}.jpg"
    pics = lambda nums, ans=None: [{"tep_hinh": img(n), "la_dap_an_dung": ans == i} for i, n in enumerate(nums)]
    base = lambda sk, dang, **kw: {"dang": dang, "cap_do_id": 0, "ky_nang": sk, "dung_thi_thu": True, "dung_on_luyen": False, **kw}

    plan = []
    for ex, pic, ok, said, py, vi in cfg["L1"]:
        plan.append((1, base("nghe", "dung_sai", tep_hinh=img(pic), loi_nghe=z(said), pinyin=py, dich_nghia=vi, phuong_an=tf(ok)), ex))
    for ex, ps, ans, said, py, vi in cfg["L2"]:
        plan.append((2, base("nghe", "chon_mot", loi_nghe=z(said), pinyin=py, dich_nghia=vi, phuong_an=pics(ps, LETTER[ans] - 1)), ex))
    plan.append((3, {
        "group": base("nghe", "ngu_lieu", phuong_an=pics([25, 26, 27, 28, 29, 30])),
        "children": [({"dang": "chon_bo_chung", "loi_nghe": z(said), "pinyin": py, "dich_nghia": vi, "dap_an_thu_tu": LETTER[ans]}, ex)
                     for ex, ans, said, py, vi in cfg["L3"]],
    }, None))
    for ex, opts, ans, said, py, vi in cfg["L4"]:
        plan.append((4, base("nghe", "chon_mot", loi_nghe=z(said), pinyin=py, dich_nghia=vi, phuong_an=words(opts, LETTER[ans] - 1)), ex))
    for ex, pic, word, py, ok, vi in cfg["R1"]:
        plan.append((5, base("doc", "dung_sai", tep_hinh=img(pic), noi_dung=word, pinyin=py, dich_nghia=vi, phuong_an=tf(ok)), ex))
    for part, opts, rows in ((6, None, cfg["R2"]), (7, cfg["R3_OPTIONS"], cfg["R3"]), (8, cfg["R4_OPTIONS"], cfg["R4"])):
        shared = pics([38, 39, 40, 41, 42, 43]) if opts is None else words(opts)
        plan.append((part, {
            "group": base("doc", "ngu_lieu", phuong_an=shared),
            "children": [({"dang": "chon_bo_chung", "noi_dung": z(s), "pinyin": py, "dich_nghia": vi, "dap_an_thu_tu": LETTER[ans]}, ex)
                         for ex, ans, s, py, vi in rows],
        }, None))
    return plan


def main() -> int:
    db = SessionLocal()
    try:
        lecturer = int(db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one())
        level = int(db.execute(text("SELECT id FROM cap_do WHERE ma = 'HSK1'")).scalar_one())

        for cfg in EXAMS_HSK1:
            if db.execute(text("SELECT 1 FROM bo_de WHERE ma_de = :m"), {"m": cfg["code"]}).first():
                print(f"· Bỏ qua {cfg['ten']} ({cfg['code']}): đã tồn tại")
                continue

            audio_rel = f"exams/{cfg['slug']}/listening.mp3"
            assert (UPLOADS / audio_rel).is_file(), f"Thiếu {audio_rel}"
            for i in range(44):
                assert (UPLOADS / f"exams/{cfg['slug']}/img/{i:03d}.jpg").is_file(), f"Thiếu ảnh {i:03d}.jpg của {cfg['code']}"

            items: list[ExamItemIn] = []
            for part, entry, example in build_plan(cfg):
                if "group" in entry:
                    payload = {**entry["group"], "cap_do_id": level, "cau_con": [c for c, _ in entry["children"]]}
                    qid = create_question(db, QuestionIn(**payload), lecturer)
                    publish_question(db, qid, lecturer)
                    child_ids = [int(r[0]) for r in db.execute(
                        text("SELECT id FROM cau_hoi WHERE cau_cha_id = :p ORDER BY id"), {"p": qid}
                    ).all()]
                    for cid, (_, is_ex) in zip(child_ids, entry["children"]):
                        items.append(ExamItemIn(cau_hoi_id=cid, phan=part, la_cau_vi_du=bool(is_ex)))
                else:
                    qid = create_question(db, QuestionIn(**{**entry, "cap_do_id": level}), lecturer)
                    publish_question(db, qid, lecturer)
                    items.append(ExamItemIn(cau_hoi_id=qid, phan=part, la_cau_vi_du=bool(example)))

            exam_id = exam_service.create_exam(db, ExamInfoIn(
                cap_do_id=level,
                ten=cfg["ten"],
                ma_de=cfg["code"],
                thoi_luong_phut=40,
                nguon=cfg["nguon"],
                tep_audio_chung=audio_rel,
            ), lecturer)
            exam_service.set_exam_items(db, exam_id, items)
            exam_service.publish_exam(db, exam_id)
            scored = sum(1 for i in items if not i.la_cau_vi_du)
            print(f"→ Đã nạp & đăng {cfg['ten']} ({cfg['code']}): {scored} câu tính điểm, {len(items) - scored} câu ví dụ.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
