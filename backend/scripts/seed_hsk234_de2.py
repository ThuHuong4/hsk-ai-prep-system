"""Tạo tệp dữ liệu chuẩn JSON và nạp Đề 2 cho HSK 2 (H20902), HSK 3 (H31002) và HSK 4 (H41002) vào Xianglingo.

Nguồn: 国家汉办/孔子学院总部 – 新汉语水平考试 HSK 2.0 (H20902, H31002, H41002) từ bộ PDF + MP3 gốc.
- Lưu 3 tệp JSON chuẩn vào backend/scripts/data/{hsk2_h20902,hsk3_h31002,hsk4_h41002}.json
- Kiểm tra toàn bộ tệp hình + âm thanh + quy tắc câu hỏi trước khi ghi CSDL
- An toàn khi chạy lại nhiều lần (idempotent theo ma_de).
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.exam_authoring.schemas.exam_payload import ExamInfoIn, ExamItemIn
from app.modules.exam_authoring.services import exam_service
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.question_rules import validate_question
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

BACKEND = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND / "scripts" / "data"
UPLOADS = BACKEND / "uploads"
LETTER = {c: i + 1 for i, c in enumerate("ABCDEF")}


def tf(ok: bool) -> list[dict]:
    return [{"noi_dung": "Đúng", "la_dap_an_dung": ok}, {"noi_dung": "Sai", "la_dap_an_dung": not ok}]


def opts_text(items: list[str], ans_letter: str | None = None) -> list[dict]:
    ans_idx = (LETTER[ans_letter] - 1) if ans_letter else None
    return [{"noi_dung": s, "la_dap_an_dung": i == ans_idx} for i, s in enumerate(items)]


def opts_img(slug: str, indices: list[int]) -> list[dict]:
    return [{"tep_hinh": f"exams/{slug}/img/{i:03d}.jpg", "la_dap_an_dung": False} for i in indices]


# ==============================================================================
# 1. HSK 2 – Đề 2 (H20902) — 60 câu tính điểm + 9 câu ví dụ
# ==============================================================================
def build_h20902() -> dict:
    slug = "hsk2_h20902"
    img = lambda n: f"exams/{slug}/img/{n:03d}.jpg"
    plan = []

    # Part 1: Nghe 1–10 (Đúng/Sai với hình)
    l1 = [
        (True, 0, True, "我们家有三个人。"),
        (True, 1, False, "我每天坐公共汽车去上班。"),
        (False, 2, False, "左边的大，右边的小。"),
        (False, 3, True, "您好！见到您很高兴。"),
        (False, 4, False, "你看，女孩子也喜欢踢足球。"),
        (False, 5, True, "咖啡来了，要不要喝一杯？"),
        (False, 6, True, "昨天是小李的生日，下班后我们去唱歌了。"),
        (False, 7, True, "太好了，我找到这本书了。"),
        (False, 8, False, "中午她给女儿买了一件衣服。"),
        (False, 9, False, "他们四个人每天都一起吃饭。"),
        (False, 10, True, "对不起，我现在很忙，十分钟后我再给你打电话。"),
        (False, 11, False, "他们开着车出去了。"),
    ]
    for ex, pic, ok, said in l1:
        plan.append({
            "part": 1, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "tep_hinh": img(pic), "loi_nghe": said, "phuong_an": tf(ok)},
        })

    # Part 2: Nghe 11–15 (6 hình A–F) & 16–20 (5 hình A–E)
    plan.append({
        "part": 2,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [12, 13, 14, 15, 16, 17])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：你喜欢什么运动？\n女：我最喜欢踢足球。", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：是今天早上的报纸吗？\n男：不是，是昨天的，今天的还没到。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：你去洗洗手。\n女：好，今天晚上给我准备什么好吃的了？", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：车怎么了？\n男：没关系，可能出了点儿小问题。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：现在雨已经不下了。\n女：是吗？我看看。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：怎么样？漂亮吗？\n男：真漂亮！我觉得非常好。", "dap_an_thu_tu": 5}, False],
        ],
    })
    plan.append({
        "part": 2,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [18, 19, 20, 21, 22])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：这个字是什么意思？\n女：在哪儿？", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：这个药一天吃几次呢？\n男：医生说一天吃两次。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：上午考得怎么样？\n女：别问了，很多题我都不会做。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：我想去北京旅游，北京哪儿最好玩儿？\n男：让我想想。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：今天还是阴天，这天气真冷。\n女：是，我穿了这么多，还觉得冷。", "dap_an_thu_tu": 1}, False],
        ],
    })

    # Part 3: Nghe 21–30
    l3 = [
        (True, "A", ["红色 [hóngsè]", "黑色 [hēisè]", "白色 [báisè]"],
         "男：小王，这里有几个杯子，哪个是你的？\n女：左边那个红色的是我的。\n问：小王的杯子是什么颜色的？"),
        (False, "C", ["工作 [gōngzuò]", "打 篮球 [dǎ lánqiú]", "看 电视 [kàn diànshì]"],
         "女：你眼睛怎么这么红？没休息好？\n男：是，昨天晚上看电视看到十二点。\n问：男的昨天晚上做什么了？"),
        (False, "A", ["饭店 [fàndiàn]", "商店 [shāngdiàn]", "教室 [jiàoshì]"],
         "男：服务员，请给我来一杯热水。谢谢。\n女：好的，不客气。\n问：他们最可能在哪儿？"),
        (False, "B", ["200 多 [200 duō]", "2000 多 [2000 duō]", "3000 多 [3000 duō]"],
         "女：你知道你们学校有多少学生吗？\n男：知道，有两千多。\n问：这个学校有多少学生？"),
        (False, "B", ["2007 年 [2007 nián]", "2008 年 [2008 nián]", "2009 年 [2009 nián]"],
         "男：你是什么时候来这个公司的？\n女：我是去年2008年来的。\n问：女的是什么时候来这个公司的？"),
        (False, "B", ["太 累 了 [tài lèi le]", "看过 了 [kànguo le]", "有 别 的 事 [yǒu bié de shì]"],
         "女：我们下午去看电影，好吗？\n男：我上个星期已经看过了，我们去游泳吧。\n问：男的为什么不去看电影？"),
        (False, "A", ["鱼 [yú]", "西瓜 [xīguā]", "鸡蛋 [jīdàn]"],
         "男：你好，鱼怎么卖呢？\n女：很便宜，两块钱一斤。\n问：男的要买什么？"),
        (False, "A", ["机场 [jīchǎng]", "医院 [yīyuàn]", "火车站 [huǒchēzhàn]"],
         "女：张小姐的飞机快到了，我们还要多长时间？\n男：没问题，我们再有五分钟就到机场了。\n问：他们要去哪儿？"),
        (False, "B", ["很 便宜 [hěn piányi]", "颜色 好 [yánsè hǎo]", "有点儿 高 [yǒudiǎnr gāo]"],
         "男：这个椅子有点儿贵，但是颜色很不错。\n女：你喜欢？那就买它吧。\n问：男的觉得这个椅子怎么样？"),
        (False, "B", ["7 月 8 号 [7 yuè 8 hào]", "8 月 7 号 [8 yuè 7 hào]", "8 月 17 号 [8 yuè 17 hào]"],
         "女：你准备哪天去中国？\n男：我买的机票是八月七号的。\n问：男的哪天去中国？"),
        (False, "C", ["爸爸 [bàba]", "妈妈 [māma]", "送 牛奶 的 [sòng niúnǎi de]"],
         "男：谁在门外？是你妈妈回来了？\n女：不是，是送牛奶的。\n问：谁在门外？"),
    ]
    for ex, ans, op, said in l3:
        plan.append({
            "part": 3, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    # Part 4: Nghe 31–35
    l4 = [
        (True, "A", ["名字 [míngzi]", "时间 [shíjiān]", "房间 号 [fángjiān hào]"],
         "女：请在这儿写您的名字。\n男：是这儿吗？\n女：不是，是这儿。\n男：好，谢谢。\n问：男的要写什么？"),
        (False, "A", ["吃 饭 [chī fàn]", "买 菜 [mǎi cài]", "喝 茶 [hē chá]"],
         "男：今天的羊肉做得很好吃，你怎么不吃了？\n女：少吃肉，多吃菜，对身体好。\n男：身体好还要多运动。\n女：那我们明天去跑步吧。\n问：他们在做什么？"),
        (False, "C", ["很 远 [hěn yuǎn]", "很 近 [hěn jìn]", "不 太 远 [bú tài yuǎn]"],
         "女：你家离学校远吗？\n男：不太远。\n女：你每天怎么去上学？\n男：有时候坐公共汽车，有时候走路去。\n问：男的家离学校远吗？"),
        (False, "C", ["妻子 [qīzi]", "妹妹 [mèimei]", "女儿 [nǚ'ér]"],
         "男：您从几岁开始学习跳舞？\n女：七岁。\n男：是吗？我女儿今年也七岁了。我希望她能和您学跳舞，可以吗？\n女：没问题，非常欢迎。\n问：男的想让谁学跳舞？"),
        (False, "C", ["天 晴 了 [tiān qíng le]", "下 雨 了 [xià yǔ le]", "下 雪 了 [xià xuě le]"],
         "女：天快黑了，我要回去了。\n男：好的。外面正在下雪，您路上慢点儿。\n女：没关系。明天见。\n男：好的。再见。\n问：现在天气怎么样？"),
        (False, "A", ["朋友 要 来 [péngyou yào lái]", "要 去 坐 船 [yào qù zuò chuán]", "要 去 上课 [yào qù shàngkè]"],
         "男：你怎么九点就睡觉了？\n女：因为明天要早起。\n男：明天星期日，你起那么早做什么？\n女：我一个朋友明天要来，船七点就到。\n问：女的为什么要早起？"),
    ]
    for ex, ans, op, said in l4:
        plan.append({
            "part": 4, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    # Part 5: Đọc 36–40 (6 hình A–F: 23..28)
    plan.append({
        "part": 5,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [23, 24, 25, 26, 27, 28])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "每 个 星期六， 我 都 去 打 篮球。", "pinyin": "Měi ge xīngqīliù, wǒ dōu qù dǎ lánqiú.", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "同学们， 你们 听 懂 了 吗？", "pinyin": "Tóngxuémen, nǐmen tīng dǒng le ma?", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "里面 有 你 最 爱 吃 的 水果。", "pinyin": "Lǐmiàn yǒu nǐ zuì ài chī de shuǐguǒ.", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "喂， 儿子 生病 了， 你 什么 时候 能 回来？", "pinyin": "Wéi, érzi shēngbìng le, nǐ shénme shíhou néng huílai?", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 来 介绍 一下， 这 是 我 丈夫。", "pinyin": "Wǒ lái jièshào yíxià, zhè shì wǒ zhàngfu.", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "现在 快 6 点 了， 我 20 分钟 后 去 公司 找 你。", "pinyin": "Xiànzài kuài _ diǎn le, wǒ _ fēnzhōng hòu qù gōngsī zhǎo nǐ.", "dap_an_thu_tu": 2}, False],
        ],
    })

    # Part 6: Đọc 41–45 (Điền từ A–F)
    plan.append({
        "part": 6,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text(["房间 [fángjiān]", "旁边 [pángbiān]", "认识 [rènshi]", "完 [wán]", "贵 [guì]", "等 [děng]"]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "这儿 的 羊肉 很 好吃， 但是 也 很 （　）。", "pinyin": "Zhèr de yángròu hěn hǎochī, dànshì yě hěn _", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "这些 题 你 什么 时候 能 做 （　）？", "pinyin": "Zhèxiē tí nǐ shénme shíhou néng zuò _", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "快 点儿， 大家 都 在 （　） 你 吃 饭 呢。", "pinyin": "Kuài diǎnr, dàjiā dōu zài _ nǐ chī fàn ne.", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "别 找 了， 手机 在 桌子 上 呢， 电脑 （　）。", "pinyin": "Bié zhǎo le, shǒujī zài zhuōzi shang ne, diànnǎo _", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 来 北京 的 第一 天 就 （　） 他 了。", "pinyin": "Wǒ lái Běijīng de dì-yī tiān jiù _ tā le.", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "男： （　） 里 有 人 吗？\n女： 请 进， 先生， 您 找 谁？", "pinyin": "_ _ li yǒu rén ma?\n_ Qǐng jìn, xiānsheng, nín zhǎo shéi?", "dap_an_thu_tu": 1}, False],
        ],
    })

    # Part 7: Đọc 46–50 (Đúng/Sai ★)
    r3 = [
        (True, True,
         "现在 是 11 点 30 分， 他们 已经 游了 20 分钟 了。\n★ 他们 11 点 10 分 开始 游泳。",
         "Xiànzài shì _ diǎn _ fēn, tāmen yǐjīng yóule _ fēnzhōng le.\n_ Tāmen _ diǎn _ fēn kāishǐ yóuyǒng."),
        (True, False,
         "我 会 跳舞， 但 跳 得 不 怎么样。\n★ 我 跳 得 非常 好。",
         "Wǒ huì tiàowǔ, dàn tiào de bù zěnmeyàng.\n_ Wǒ tiào de fēicháng hǎo."),
        (False, True,
         "我 知道 她 的 名字， 她 姓 杨， 叫 杨 笑笑， 她 姐姐 是 我 同学。\n★ 我 认识 杨 笑笑 的 姐姐。",
         "Wǒ zhīdào tā de míngzi, tā xìng Yáng, jiào Yáng Xiàoxiao, tā jiějie shì wǒ tóngxué.\n_ Wǒ rènshi Yáng Xiàoxiao de jiějie."),
        (False, False,
         "我 的 一 个 朋友 正在 找 房子， 希望 住 得 离 公司 近 一些， 这样 他 每 天 早上 就 可以 7 点 起床， 比 现在 多 睡 一 个 小时。\n★ 朋友 现在 每 天 7 点 起床。",
         "Wǒ de yí ge péngyou zhèngzài zhǎo fángzi, xīwàng zhù de lí gōngsī jìn yìxiē, zhèyàng tā měi tiān zǎoshang jiù kěyǐ _ diǎn qǐchuáng, bǐ xiànzài duō shuì yí ge xiǎoshí.\n_ Péngyou xiànzài měi tiān _ diǎn qǐchuáng."),
        (False, False,
         "我 喜欢 猫， 但是 丈夫 不 喜欢， 所以 到 现在 家 里 也 没有 猫。 我 希望 有 一 天 能 有 一 个 小猫。\n★ 我 丈夫 想 要 一 个 小猫。",
         "Wǒ xǐhuan māo, dànshì zhàngfu bù xǐhuan, suǒyǐ dào xiànzài jiā li yě méiyǒu māo. Wǒ xīwàng yǒu yì tiān néng yǒu yí ge xiǎomāo.\n_ Wǒ zhàngfu xiǎng yào yí ge xiǎomāo."),
        (False, True,
         "从 我 家 到 北京， 坐 火车 就 5 个 小时， 比 坐 飞机 便宜 很 多。 所以， 明天 我 准备 坐 火车 去。\n★ 我 明天 去 北京。",
         "Cóng wǒ jiā dào Běijīng, zuò huǒchē jiù _ ge xiǎoshí, bǐ zuò fēijī piányi hěn duō. Suǒyǐ, míngtiān wǒ zhǔnbèi zuò huǒchē qù.\n_ Wǒ míngtiān qù Běijīng."),
        (False, False,
         "李哥， 赵 老师 让 我 告诉 你， 你 的 电影票 买到 了。\n★ 李哥 正在 看 电影。",
         "Lǐgē, Zhào lǎoshī ràng wǒ gàosu nǐ, nǐ de diànyǐngpiào mǎidào le.\n_ Lǐgē zhèngzài kàn diànyǐng."),
    ]
    for ex, ok, s, py in r3:
        plan.append({
            "part": 7, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "pinyin": py, "phuong_an": tf(ok)},
        })

    # Part 8: Đọc 51–55 & 56–60 (Ghép câu liên quan)
    plan.append({
        "part": 8,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text([
                "别 笑 了， 我 说 的 是 真 的。 [Bié xiào le, wǒ shuō de shì zhēn de.]",
                "还 可以， 不 到 300 元。 [Hái kěyǐ, bú dào _ yuán.]",
                "这儿 有 商店 吗？ 我 想 去 买 点儿 东西。 [Zhèr yǒu shāngdiàn ma? Wǒ xiǎng qù mǎi diǎnr dōngxi.]",
                "是 吗？ 我 的 手表 慢 了？ [Shì ma? Wǒ de shǒubiǎo màn le?]",
                "他 在 哪儿 呢？ 你 看见 他 了 吗？ [Tā zài nǎr ne? Nǐ kànjiàn tā le ma?]",
                "那 我 和 你 一起 去。 [Nà wǒ hé nǐ yìqǐ qù.]",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "他 还 在 教室 里 学习。", "pinyin": "Tā hái zài jiàoshì li xuéxí.", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "9 点？ 现在 已经 9 点 25 了。", "pinyin": "_ diǎn? Xiànzài yǐjīng _ diǎn _ le.", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 家 的 狗 喜欢 吃 苹果。", "pinyin": "Wǒ jiā de gǒu xǐhuan chī píngguǒ.", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "你 的 自行车 是 白色 的？ 真 漂亮， 贵 吗？", "pinyin": "Nǐ de zìxíngchē shì báisè de? Zhēn piàoliang, guì ma?", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "鸡蛋 吃 完 了， 下午 我 再 买 一些。", "pinyin": "Jīdàn chī wán le, xiàwǔ wǒ zài mǎi yìxiē.", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "向 前 走， 就 在 那儿。", "pinyin": "Xiàng qián zǒu, jiù zài nàr.", "dap_an_thu_tu": 3}, False],
        ],
    })
    plan.append({
        "part": 8,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text([
                "我 从 您 这儿 学了 很 多。 [Wǒ cóng nín zhèr xuéle hěn duō.]",
                "新年 快乐！ [Xīnnián kuàilè!]",
                "我 弟弟 在 北京 大学 读 书， 今年 是 第三 年 了。 [Wǒ dìdi zài Běijīng Dàxué dú shū, jīnnián shì dì-sān nián le.]",
                "听说 他 病 了， 我们 找 时间 去 看看 他 吧。 [Tīngshuō tā bìng le, wǒmen zhǎo shíjiān qù kànkan tā ba.]",
                "这个 是 下午 送？ 送 到 哪儿？ [Zhège shì xiàwǔ sòng? Sòng dào nǎr?]",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "今天 是 1 月 1 日。", "pinyin": "Jīntiān shì _ yuè _ rì.", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "等 一下， 我 打 电话 问 一下。", "pinyin": "Děng yíxià, wǒ dǎ diànhuà wèn yíxià.", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "他 会 说 汉语？", "pinyin": "Tā huì shuō Hànyǔ?", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "星期六 怎么样？", "pinyin": "Xīngqīliù zěnmeyàng?", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "希望 我 的 回答 能 对 你 有 帮助。", "pinyin": "Xīwàng wǒ de huídá néng duì nǐ yǒu bāngzhù.", "dap_an_thu_tu": 1}, False],
        ],
    })

    return {
        "exam": {
            "code": "H20902",
            "level": "HSK2",
            "ten": "HSK 2 – Đề 2",
            "phut": 55,
            "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（二级）H20902",
            "audio": f"exams/{slug}/listening.mp3",
            "img_dir": f"exams/{slug}/img",
        },
        "plan": plan,
    }


# ==============================================================================
# 2. HSK 3 – Đề 2 (H31002) — 80 câu tính điểm + 10 câu ví dụ
# ==============================================================================
def build_h31002() -> dict:
    slug = "hsk3_h31002"
    plan = []

    # Part 1: Nghe 1–5 (6 hình 0..5) & 6–10 (5 hình 6..10)
    plan.append({
        "part": 1,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [0, 1, 2, 3, 4, 5])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：喂，请问张经理在吗？\n女：他正在开会，您半个小时以后再打，好吗？", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：喝点儿水吧，今天踢得怎么样？\n男：我们班的水平比他们高，我们进了五个球！", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：每天都要洗碗和盘子，累不累？\n女：不累，我们家那位做饭，我来洗是应该的。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：十四床的病人今天好些了吧？\n男：好多了，下个星期应该可以出院了。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：我们是去年秋天结婚的，你看，这张照片就是那会儿照的。\n女：你爱人真漂亮！", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：你看见我的照相机了吗？我记得放在包里了啊。\n男：没看见，别着急，慢慢找。", "dap_an_thu_tu": 2}, False],
        ],
    })
    plan.append({
        "part": 1,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [6, 7, 8, 9, 10])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：姐，祝您生日快乐！\n女：谢谢你，谢谢你的礼物。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：喂，出门前再检查检查你的行李，别又忘了什么东西。\n男：这次不会了，已经检查过两次了。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：你看看这段话这样写怎么样？\n女：除了这个句子意思有些不清楚外，其他都不错。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：怎么不看新闻了？\n男：世界杯七点半开始，我等了四年了。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：爸爸年轻的时候真有意思，这是真的吗？\n女：当然是真的，他那时候还特别喜欢送我花。", "dap_an_thu_tu": 5}, False],
        ],
    })

    # Part 2: Nghe 11–20 (Đúng/Sai ★)
    l2 = [
        (True, True, "★ 他希望自己很健康。", "为了让自己更健康，他每天都花一个小时去锻炼身体。\n★ 他希望自己很健康。"),
        (True, False, "★ 那块儿手表不是他的。", "今天我想早点儿回家。看了看手表，才五点。过了一会儿再看表，还是五点，我这才发现我的手表不走了。\n★ 那块儿手表不是他的。"),
        (False, False, "★ 弟弟正在看电视。", "把电视声音关小点儿，你弟弟明天考试，正在复习呢，别影响他。\n★ 弟弟正在看电视。"),
        (False, True, "★ 这个题很难。", "你看看这个题？开始大家以为很容易，没想到，到下课也没做出来。\n★ 这个题很难。"),
        (False, True, "★ 宾馆旁边有个公园。", "这个宾馆的南边有一个公园，奇怪的是，这张地图上把公园画在宾馆的北边了。\n★ 宾馆旁边有个公园。"),
        (False, False, "★ 他不喜欢小狗。", "我有一条小狗，和它在一起的时间越久，我越觉得它聪明、可爱。\n★ 他不喜欢小狗。"),
        (False, False, "★ 他这个周末去看电影。", "这个周末有个重要的会议，所以不能和你一起去看那个电影了，对不起，下周怎么样？\n★ 他这个周末去看电影。"),
        (False, True, "★ 妈妈晚上不在家吃饭。", "你妈晚上和朋友们在外面吃饭，所以我们要自己做饭了，让我看看冰箱里有什么吃的。\n★ 妈妈晚上不在家吃饭。"),
        (False, False, "★ 房间里很冷。", "客人马上就要来了，你去告诉李小姐先把房间里的空调打开，今天太热了。\n★ 房间里很冷。"),
        (False, True, "★ 花园不大。", "这个房子真的很不错，厨房和洗手间都很大，房子后面还有一个小花园，像您这么喜欢小动物，有个花园会很方便。\n★ 花园不大。"),
        (False, False, "★ 他要去学校。", "这件事电话里讲不明白，我们还是见面说吧，一个小时后我到公司，你在办公室等我。\n★ 他要去学校。"),
        (False, True, "★ 比赛要求有变化。", "这次比赛的新要求和需要注意的一些问题网上都有，你上网看一下，回去跟同学们也说一下。\n★ 比赛要求有变化。"),
    ]
    for ex, ok, s, said in l2:
        plan.append({
            "part": 2, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "loi_nghe": said, "phuong_an": tf(ok)},
        })

    # Part 3: Nghe 21–30
    l3 = [
        (True, "A", ["开门", "拿东西", "去超市买东西"],
         "男：小王，帮我开一下门，好吗？谢谢！\n女：没问题。您去超市了？买了这么多东西。\n问：男的想让小王做什么？"),
        (False, "B", ["一直很好", "需要提高", "提高很快"],
         "女：我发现，你现在很爱看新闻。\n男：我其实对新闻没兴趣，主要是想提高提高我的普通话水平。\n问：男的觉得自己的普通话怎么样？"),
        (False, "A", ["住得近", "要运动", "工作忙"],
         "男：你最近比以前来得早了，搬家了？\n女：是啊，你不知道？我上个月就搬家了，走路十分钟就到。\n问：女的为什么来得早？"),
        (False, "C", ["借书", "做游戏", "打电话"],
         "女：您好，3260号为您服务，请问您查哪儿？\n男：你好，请帮我查一下国家图书馆的电话，谢谢。\n问：男的在做什么？"),
        (False, "A", ["明天", "春节", "星期日"],
         "男：明天上午我们去看你爷爷，你作业写完了没？\n女：我今天一定能完成作业，相信我好了。\n问：他们哪天去爷爷家？"),
        (False, "B", ["院长", "校长", "市长"],
         "女：您请坐，王校长正在开会，会议马上就结束了。\n男：谢谢。我问您一下，贵校有多少在读学生？一万？\n问：男的要找谁？"),
        (False, "C", ["邻居", "老师和学生", "丈夫和妻子"],
         "男：别说话，你听，这是什么声音？\n女：你不知道？儿子昨天买了两只小鸟，一只红色的，一只黄色的。\n问：他们最可能是什么关系？"),
        (False, "C", ["牙疼", "不爱吃", "他已经刷牙了"],
         "女：新买的这种糖特别甜，很好吃，你吃一块儿？\n男：不，我已经刷牙了。\n问：男的为什么不吃糖？"),
        (False, "B", ["机场", "超市", "地铁"],
         "男：你这儿的环境很好，很安静。\n女：环境是不错，买东西也方便，附近就有超市，就是离地铁远。\n问：这儿离哪里近？"),
        (False, "B", ["买水果", "来接她", "去上班"],
         "女：我中午买了两箱苹果，你开车来接我吧。\n男：好，等一会儿下班后我给你打电话。\n问：女的想让男的做什么？"),
        (False, "A", ["打车", "骑自行车", "坐公共汽车"],
         "男：您没去火车站？您的司机呢？\n女：他今天有点事，我叫了辆出租车，几分钟后就到楼下。\n问：女的打算怎么去火车站？"),
    ]
    for ex, ans, op, said in l3:
        plan.append({
            "part": 3, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    # Part 4: Nghe 31–40
    l4 = [
        (True, "C", ["洗澡", "吃饭", "看电视"],
         "女：晚饭做好了，准备吃饭了。\n男：等一会儿，比赛还有三分钟就结束了。\n女：快点儿吧，一起吃，菜冷了就不好吃了。\n男：你先吃，我马上就看完了。\n问：男的在做什么？"),
        (False, "C", ["饭馆", "商店", "医院"],
         "男：我给你开点儿药，这段时间注意休息，不要太累。\n女：好的，我会注意的。\n男：还有，咖啡和啤酒要少喝，不要吃羊肉和鱼。\n女：好，谢谢您。\n问：他们在哪里？"),
        (False, "C", ["哭了", "饿了", "鼻子不舒服"],
         "女：哥，刘阿姨是不是生气了？\n男：没有啊。她只是鼻子有点儿不舒服。\n女：那就好，我以为她因为什么不高兴了。\n男：你不用那么客气。走，去看表演吧。\n问：刘阿姨怎么了？"),
        (False, "C", ["喜欢跳舞", "经常跑步", "想去爬山"],
         "男：下个星期六我准备去爬山。\n女：你很长时间没锻炼身体了，要小心点儿。\n男：没关系，最近我不是开始跑步了吗？\n女：最近？你是从昨天才开始跑步的。\n问：关于男的，可以知道什么？"),
        (False, "A", ["2", "3", "4"],
         "女：请问，汉语词典在几层？\n男：在二层，二层右边。\n女：还有一个问题，我可以借几天呢？\n男：对不起，词典不借出的，只能在这儿用。\n问：女的应该去第几层？"),
        (False, "A", ["不胖", "很热情", "口渴了"],
         "男：别吃了，你已经吃了三块儿蛋糕了。\n女：这是最后一块儿。\n男：你总是吃甜的东西，不怕变胖吗？\n女：你放心，我们家的人都很瘦，吃不胖，我也一样。\n问：关于女的，可以知道什么？"),
        (False, "B", ["不努力", "没兴趣", "迟到了"],
         "女：别难过了，考试成绩不是最重要的。\n男：我的分数太低了。\n女：但是你努力了。你的问题是你对历史没兴趣。\n男：是，如果我喜欢历史跟我喜欢音乐一样该多好。\n问：他的历史成绩为什么不好？"),
        (False, "A", ["黑色的", "蓝色的", "绿色的"],
         "男：带上伞吧，天阴了，可能会下雨。\n女：知道了，我带着呢。\n男：伞还在桌子上呢，你别忘了。\n女：我拿的是那把黑色的，短的那把。\n问：女的拿了哪把伞？"),
        (False, "C", ["吃面包", "喝果汁", "简单点儿"],
         "女：吃了午饭再走吧，我做两个菜，很快的。\n男：简单吃点儿面条儿就可以了。\n女：好，那我去做鸡蛋面，你先喝杯茶。\n男：要不要我帮忙啊？\n问：男的希望怎么样？"),
        (False, "C", ["三天", "半年", "还没定"],
         "男：你这次要离开多长时间？\n女：还没决定，一周或者两周吧。\n男：你这是第几次去那儿了？\n女：第三次。有什么事给我打电话、写电子邮件都可以。\n问：女的要出去多长时间？"),
        (False, "B", ["选帽子", "选衣服", "卖衣服"],
         "女：我明天穿什么衣服好？你帮我选选？\n男：你想穿裙子还是裤子？\n女：我想穿裙子，这条白色的怎么样？\n男：同意。那穿哪双鞋呢？\n问：他们在做什么？"),
    ]
    for ex, ans, op, said in l4:
        plan.append({
            "part": 4, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    # Part 5: Đọc 41–45 & 46–50
    plan.append({
        "part": 5,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text([
                "这是一个很好的机会，但我对自己的游泳成绩不太满意。",
                "我刚才在电梯门口遇到经理了。",
                "这儿的冬天就是这样，慢慢地你就习惯了。",
                "我的电脑又不能用了，你来帮我看看？",
                "当然。我们先坐公共汽车，然后换地铁。",
                "你们就别担心了。",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "你知道怎么去那儿吗？", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "这次比赛，世界很多国家的运动员都来参加。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "外面的风刮得真大！", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "你那个太旧了，换一个吧。很便宜，就两三千块钱。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "孩子已经18岁了，知道怎么照顾自己。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "他让我告诉你，下午两点半在公司会议室开会。", "dap_an_thu_tu": 2}, False],
        ],
    })
    plan.append({
        "part": 5,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text([
                "你认识那位先生，是吗？",
                "妹妹在北京上大学，三年级。",
                "他感冒了，有点儿发烧。",
                "女儿第一次骑马的时候比较害怕。",
                "叔叔，您愿意教我吗？",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "终于把教室打扫干净了，她洗澡去了。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "你10岁了？体育怎么样？喜欢打篮球吗？", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "他是我的同事，需要我为你介绍一下吗？", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "那你在家休息几天吧。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "现在，她觉得那是一件非常快乐的事情。", "dap_an_thu_tu": 4}, False],
        ],
    })

    # Part 6: Đọc 51–55 & 56–60 (Điền từ)
    plan.append({
        "part": 6,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text(["向", "然后", "花", "筷子", "声音", "相同"]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "她说话的（　）多好听啊！", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "您站中间就可以了，好，再（　）左边一点儿，非常好！", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "服务员，请你再给我拿一双（　）。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "虽然这两个问题有不一样的地方，但是解决的办法是（　）的。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "这次出去旅游，一共去了7个城市，（　）了一万多块钱。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "明天早上我先去银行，（　）再去找你。", "dap_an_thu_tu": 2}, False],
        ],
    })
    plan.append({
        "part": 6,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text(["关心", "差", "突然", "爱好", "节目", "还"]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "A：你有什么（　）？\nB：我喜欢体育。", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "A：下一个（　）是什么？\nB：下面为大家唱歌的是王医生，歌的名字是《十五的月亮》，大家欢迎！", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：我的飞机票呢？怎么（　）找不到了？\nB：是不是和报纸放一起了？", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：现在几点了？我的手表又坏了。\nB：我看一下，现在（　）一刻九点。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：那本书你（　）了？\nB：对，没什么意思，而且很多地方看不懂。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：那个药的作用怎么样？脚好些了吗？\nB：好多了，谢谢您的（　）。", "dap_an_thu_tu": 1}, False],
        ],
    })

    # Part 7: Đọc 61–70
    r3 = [
        (True, "C", ["8点", "8点半", "9点"], "您是来参加今天会议的吗？您来早了一点儿，现在才8点半。您先进来坐吧。\n★ 会议最可能几点开始？"),
        (False, "A", ["树下", "椅子上", "办公室"], "每次经过他家门口的时候，我几乎都能看到他的那只老猫在树下睡觉。\n★ 那只猫经常在哪儿睡觉？"),
        (False, "A", ["健康", "帮助别人", "发现问题"], "奶奶经常对我说：“吃饭七分饱。”“七分”就是70%的意思。很多中国人认为“吃饭七分饱”对身体健康很有帮助。\n★ “吃饭七分饱”是为了："),
        (False, "B", ["常下雪", "很有名", "有很多故事"], "这里的香蕉非常有名，每年8月这里会举行一个香蕉节，所以，夏季有很多人来这里玩儿。\n★ 这个地方："),
        (False, "A", ["比较矮", "腿很长", "有60公斤"], "他姓高，但是长得不高，只有一米六。同事们都说：“我们以后叫你小高吧。”他笑着回答：“当然可以，过去朋友们都这么叫我。”\n★ 关于他，可以知道什么？"),
        (False, "A", ["他起得早", "天气不错", "他工作很认真"], "太阳从西边出来了吗？他今天怎么这么早就起床了？他一般都要睡到8点以后才起床。\n★ 根据这段话，可以知道今天："),
        (False, "B", ["写字", "写短信", "做练习"], "手机使我们的学习、工作越来越方便，除了打电话、写短信外，很多手机还可以照相，有时候真的方便极了。\n★ 手机经常被用来："),
        (False, "C", ["关灯", "见面", "离开"], "“再见”是一个很有意思的词语。“再见”表示“再一次见面”，所以人们离开时说“再见”，其实也是希望以后再见面。\n★ “再见”出现在什么时候？"),
        (False, "B", ["站着", "低着头", "多喝牛奶"], "西瓜的汁儿多，吃的时候小心点儿，要低下头，不要吃得脸上、衬衫上都是。还有，不要一边吃一边说话。\n★ 吃西瓜时须："),
        (False, "B", ["元", "角", "分"], "你看，这上面写着1.21元，前面的1表示元，中间的2表示角，最后的1表示分。明白了吗？\n★ 中间的数字表示："),
        (False, "C", ["画儿", "手表", "铅笔"], "我是一个中学老师，教学生画画儿。每次下课前，我会把下次学生要带的东西写在黑板上，但每次上课时，总会有学生忘了拿铅笔。\n★ 学生会忘记拿什么？"),
    ]
    for ex, ans, op, s in r3:
        plan.append({
            "part": 7, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "phuong_an": opts_text(op, ans)},
        })

    # Part 8: Viết 71–75 (Sắp xếp từ thành câu)
    w1 = [
        (True, ["小船", "上", "一", "河", "条", "有"], ["河上有一条小船。"]),
        (False, ["先", "菜单", "我们", "看看"], ["我们先看看菜单。"]),
        (False, ["她", "带", "忘了", "护照"], ["她忘了带护照。"]),
        (False, ["很", "这些", "葡萄", "新鲜"], ["这些葡萄很新鲜。"]),
        (False, ["都", "黑色的", "熊猫的", "眼睛和耳朵", "是"], ["熊猫的眼睛和耳朵都是黑色的。"]),
        (False, ["你", "冷水", "洗澡", "用", "敢不敢"], ["你敢不敢用冷水洗澡？"]),
    ]
    for ex, pieces, acc in w1:
        plan.append({
            "part": 8, "ex": ex,
            "q": {"dang": "sap_xep", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": "完成句子。", "phuong_an": [{"noi_dung": p} for p in pieces], "dap_an_chap_nhan": acc},
        })

    # Part 9: Viết 76–80 (Điền chữ Hán theo Pinyin)
    w2 = [
        (True, "没（ guān ）系，别难过，高兴点儿。", ["关"]),
        (False, "他一直都很关心别（ ren ）。", ["人"]),
        (False, "你的头发（ tài ）长了，像草一样。", ["太"]),
        (False, "就在这条街的东边，有（ ge ）眼镜店。", ["个"]),
        (False, "今天是晴天，没有（ yún ）。", ["云"]),
        (False, "我来中国，除了学习汉语，还希望了解更多的中国（ wén ）化。", ["文"]),
    ]
    for ex, s, acc in w2:
        plan.append({
            "part": 9, "ex": ex,
            "q": {"dang": "dien_chu", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "goi_y": "Điền chữ Hán theo pinyin trong ngoặc", "dap_an_chap_nhan": acc},
        })

    return {
        "exam": {
            "code": "H31002",
            "level": "HSK3",
            "ten": "HSK 3 – Đề 2",
            "phut": 90,
            "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（三级）H31002",
            "audio": f"exams/{slug}/listening.mp3",
            "img_dir": f"exams/{slug}/img",
        },
        "plan": plan,
    }


# ==============================================================================
# 3. HSK 4 – Đề 2 (H41002) — 100 câu tính điểm + 10 câu ví dụ
# ==============================================================================
def build_h41002() -> dict:
    slug = "hsk4_h41002"
    img = lambda n: f"exams/{slug}/img/{n:03d}.jpg"
    plan = []

    # Part 1: Nghe 1–10 (Đúng/Sai ★)
    l1 = [
        (True, True, "★ 他打算下午去银行。", "我想去办个信用卡，今天下午你有时间吗？陪我去一趟银行？\n★ 他打算下午去银行。"),
        (True, False, "★ 他喜欢看电视广告。", "现在我很少看电视，其中一个原因是，广告太多了，不管什么时间，也不管什么节目，只要你打开电视，总能看到那么多的广告，浪费我的时间。\n★ 他喜欢看电视广告。"),
        (False, False, "★ 签证已经办好了。", "明天就要去使馆办签证了，邀请信竟然还没寄到，这可怎么办？\n★ 签证已经办好了。"),
        (False, True, "★ 现在她也做妈妈了。", "女儿出生以后，我才知道做妈妈有多么不容易。因此，我更加理解我的父母了，也感谢他们这么多年来给我的爱。\n★ 现在她也做妈妈了。"),
        (False, True, "★ 小王今天要加班。", "小王，这份材料明天早上就要用，得请你翻译一下，晚上十点之前一定要完成，翻译好后打印一份给经理，辛苦你了。\n★ 小王今天要加班。"),
        (False, True, "★ 节日是文化的一部分。", "节日是文化的一部分，所以，如果想了解一个国家的文化，我们可以从了解这个国家的节日开始。\n★ 节日是文化的一部分。"),
        (False, False, "★ 王教授脾气很大。", "三十七岁的王教授，在我们学校很有名，不但会三种语言，而且会写小说，各方面都很优秀。\n★ 王教授脾气很大。"),
        (False, False, "★ 真正的爱情不需要浪漫。", "怎么样才能找到适合自己的人？两个人共同生活，不仅需要浪漫的爱情，更需要性格上互相吸引，最重要的是，两个人都要有对家的责任感。\n★ 真正的爱情不需要浪漫。"),
        (False, False, "★ 年轻人喜欢早上锻炼身体。", "只要注意一下，你会发现，早上的公园里、街道上，早起锻炼的人中，老年人很多而年轻人很少。\n★ 年轻人喜欢早上锻炼身体。"),
        (False, False, "★ 小林正在找工作。", "小林，这次的招聘是由你负责吧？李教授介绍了他的一个学生，是个博士，条件还不错，这是他的申请材料，你看看。\n★ 小林正在找工作。"),
        (False, True, "★ 应该总结过去的经验。", "回忆过去，有苦也有甜，有伤心、难过也有幸福、愉快，有很多故事让人难以忘记，有很多经验值得我们总结。\n★ 应该总结过去的经验。"),
        (False, True, "★ 广告词应该简短。", "理想的广告词应该简短，一般六到十二个字比较合适，不应该太长，否则观众不易记住，也就流行不起来。\n★ 广告词应该简短。"),
    ]
    for ex, ok, s, said in l1:
        plan.append({
            "part": 1, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "loi_nghe": said, "phuong_an": tf(ok)},
        })

    # Part 2: Nghe 11–25
    l2 = [
        (True, "D", ["去机场", "快到了", "油是满的", "有加油站"], "女：该加油了，去机场的路上有加油站吗？\n男：有，你放心吧。\n问：男的主要是什么意思？"),
        (False, "A", ["正在做饭", "正在购物", "在擦窗户", "在收拾厨房"], "男：妈，您的手机响了。\n女：肯定是你爸，你接一下，就说妈正在做午饭呢。\n问：关于女的，可以知道什么？"),
        (False, "A", ["能力", "数量", "知识", "专业"], "女：你看电视上的报道了吗？今年十个大学毕业生竞争一个工作。\n男：关键还是看能力，有能力的人不怕找不到好工作。\n问：男的认为什么是关键？"),
        (False, "D", ["非常鲜", "很好喝", "太辣了", "太咸了"], "男：我的天，这个西红柿汤你放了多少盐啊！\n女：我尝尝，呀，对不起，盐是太多了。\n问：汤的味道怎么样？"),
        (False, "C", ["没兴趣", "票很贵", "票不好买", "喜欢打网球"], "女：下星期首都体育馆有场羽毛球比赛，我们一起去看？\n男：票恐怕很难买到吧？\n问：男的主要是什么意思？"),
        (False, "A", ["换裤子", "戴帽子", "洗个澡", "散散步"], "男：明天我穿这件衬衫怎么样？\n女：衬衫没问题，但是裤子要换一条黑色的，另外，你该理发了。\n问：女的让男的做什么？"),
        (False, "D", ["夫妻", "母子", "父女", "姐弟"], "女：什么时候让我们见见你的女朋友？\n男：没问题，姐，我们正商量着下个周末请家里人一起吃个饭呢。\n问：说话人是什么关系？"),
        (False, "D", ["今天上午", "明天下午", "明天晚上", "后天上午"], "男：小张，原定后天上午的会改在明天下午两点了，你通知一下其他人。\n女：好的，经理，我现在就打电话。\n问：会议原来准备什么时候开？"),
        (False, "B", ["太旧了", "是货梯", "电梯坏了", "他们去二层"], "女：我们还是坐别的电梯吧，你看电梯门上写着“货梯”。\n男：好吧，去那边吧。\n问：他们为什么不坐这个电梯？"),
        (False, "C", ["送给邻居", "要多运动", "搬到院子里", "再多买几朵"], "男：奇怪，这花儿才买来几天，怎么叶子就黄了？\n女：植物需要阳光，咱把它搬到院子里，可能会好些。\n问：女的有什么意见？"),
        (False, "B", ["一刻钟", "20分钟", "40分钟", "一个小时"], "女：师傅，我去火车站。大概要多长时间，半小时能到吗？\n男：现在不堵车，估计二十分钟就能到。\n问：去火车站需要多长时间？"),
        (False, "B", ["人与自然", "动物世界", "经济与法", "体育新闻"], "男：你喜欢看这样的节目？\n女：对，《动物世界》很精彩啊，还可以丰富知识。你不喜欢？\n问：女的喜欢看什么节目？"),
        (False, "A", ["饺子", "米饭", "面条", "面包"], "女：我现在去菜市场买菜，你中午想吃点儿什么？\n男：随便，或者我们吃饺子好不好？\n问：男的中午想吃什么？"),
        (False, "A", ["很顺利", "天气很热", "时间很紧张", "遇到些麻烦"], "男：王校长，这次出差还顺利吧？\n女：挺顺利的，安排得很好，还顺便在北京玩儿了两天。\n问：这次出差，情况怎么样？"),
        (False, "D", ["商店", "宾馆", "教室", "办公室"], "女：小刘，帮我把这两页材料传真给李记者，他下周的一篇报道里要用这些数字。\n男：好，他的传真号码是多少？\n问：对话最可能发生在哪儿？"),
        (False, "B", ["减肥", "爬山", "踢足球", "打篮球"], "男：终于爬上来了，累死我了，这山太高了。\n女：看来你确实缺少锻炼，以后每天跟我一块儿跑步吧。\n问：他们最可能在做什么？"),
    ]
    for ex, ans, op, said in l2:
        plan.append({
            "part": 2, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    # Part 3: Nghe 26–35 (hội thoại 4 lượt) + 36–45 (5 đoạn văn × 2 câu)
    l3_single = [
        (True, "C", ["两点", "3点", "3：30", "6点"], "男：把这个文件复印五份，一会儿拿到会议室发给大家。\n女：好的。会议是下午三点吗？\n男：改了。三点半，推迟了半个小时。\n女：好，六零二会议室没变吧？\n男：对，没变。\n问：会议几点开始？"),
        (False, "C", ["他是警察", "他是负责人", "他熟悉上海", "他放暑假了"], "女：王律师，我有一个朋友想来上海做生意。\n男：好啊，上海这个城市大，市场也大，机会也多。\n女：可是我们对当地的情况都不太了解。\n男：可以问我啊，我在这儿工作快二十年了，我熟悉啊。\n问：男的为什么说可以问他？"),
        (False, "A", ["女的刚回来", "他们在机场", "男的很失望", "男的要去上班"], "男：真抱歉，本来我该去火车站接你的。\n女：没关系，我打个车就回来了，很方便。你那篇材料写完没？\n男：差不多了，我再检查一遍，就可以交了。\n女：那你快写吧，写完早点儿休息。\n问：根据对话，可以知道什么？"),
        (False, "D", ["被批评了", "被人骗了", "赚了很多钱", "找到一百元"], "女：今天打扫房间，你猜我找到什么了？\n男：看你这么兴奋，难道找到人民币了？笑什么？究竟是什么？\n女：你真聪明，我在咱们床底下找到一百块钱。\n男：那是我的，我昨天好像丢了一百。\n女：我不相信！它现在是我的。\n问：女的怎么了？"),
        (False, "C", ["银行", "洗手间", "小商店", "吸烟室"], "男：请问，附近哪儿可以复印？\n女：图书馆一楼东边有几台自助复印机。\n男：除了那儿，还有其他地方吗？\n女：那你要去学校外面了，南门对面有个小商店，那儿也可以复印。\n问：根据对话，男的最可能去哪儿？"),
        (False, "D", ["健康", "旅游", "饮食", "花费"], "女：这个月家里一共花了五千多块。\n男：这么多？你不会是算错了吧？\n女：没算错。光买沙发和冰箱就花了四千多。\n男：明白了。下个月不会花这么多了。\n问：他们在谈什么？"),
        (False, "D", ["收到短信了", "她今天结婚", "衣服很漂亮", "得到一个礼物"], "男：小姐，您是今天第一个来我们超市的客人，我们准备了一个小礼物送给您。\n女：真的吗？谢谢你！太高兴了。\n男：这是我们超市送您的环保购物袋，祝您购物愉快。\n女：谢谢。\n问：女的为什么很高兴？"),
        (False, "C", ["4月", "5月", "8月", "10月"], "女：你好，我想报名参加这个月的普通话水平考试。\n男：对不起，报名工作今天上午刚结束。\n女：啊，那下一次考试是什么时候？\n男：八月十五号，报名时间您可以上我们的网站查一下。\n问：下一次考试是几月？"),
        (False, "B", ["很勇敢", "很诚实", "很可爱", "很有礼貌"], "男：您能给我们介绍一些您的成功经验吗？\n女：我觉得要重视平时的积累，要多向周围的人学习。\n男：那您觉得您最大的优点是什么呢？\n女：是诚实。\n问：女的觉得自己怎么样？"),
        (False, "C", ["他很热情", "他力气大", "他是研究生", "他文章写得好"], "女：大学毕业后就没联系了，你现在在哪儿工作呢？\n男：毕业后在老家工作了一年，然后又考上了北京大学，读研究生。\n女：真厉害！是硕士了。你读什么专业？几年？\n男：教育学，三年。\n问：女的为什么说男的很厉害？"),
        (False, "A", ["迟到", "赢不了", "会下雨", "不认识路"], "男：油箱里剩的油不多了，看看哪儿有加油站。\n女：前面就有一个，大概有四五公里远。\n男：好，那我就放心了，刚才我还有点儿担心来不及呢。\n女：航班是十点的，来得及。\n问：男的刚才担心什么？"),
    ]
    for ex, ans, op, said in l3_single:
        plan.append({
            "part": 3, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    l3_groups = [
        ("邓亚萍是中国的乒乓球运动员，但是她的身高只有一米五五，很多人认为她并不适合打乒乓球。可是她通过努力，改变了人们的这一看法。她十五岁成为亚洲第一，十六岁获得世界第一。",
         [("关于邓亚萍，可以知道什么？", "B", ["很瘦", "个子矮", "十分骄傲", "爱好历史"]),
          ("邓亚萍什么时候获得亚洲第一？", "A", ["15岁", "16岁", "25岁", "26岁"])]),
        ("同学们正在教室里学习，准备下星期的考试。班长忽然跑进来，大声说：“告诉大家一个好消息和一个坏消息。好消息是下星期不考试了！”同学们高兴得跳了起来，班长又说：“坏消息是下星期的考试，改到今天了。”",
         [("消息是谁通知的？", "B", ["老师", "班长", "校长", "院长"]),
          ("坏消息是什么？", "C", ["要考数学", "作业很多", "考试提前了", "考试成绩不好"])]),
        ("他是一位著名的演员。有一次，一个地方举行一个比赛，看谁表演得更像他。参加的人有三四十个，他自己也报名参加了，但没有告诉任何人，结果他得的竟是第三名。他觉得这是他一生中最大的一个笑话。",
         [("他参加的是什么比赛？", "C", ["游泳", "骑马", "表演", "画画儿"]),
          ("他为什么觉得很好笑？", "D", ["比赛很乱", "大家都很笨", "他们都很胖", "他没得第一名"])]),
        ("进入冬季，气候干燥，怎样才能保护皮肤，让别人看不出自己的年龄？我们的“水之印象”可以让您的皮肤在干燥的冬季喝饱水。我们现在正举办免费试用活动，很多人用过之后，都说效果非常好，您还在等什么？",
         [("“水之印象”有什么作用？", "B", ["让人更成熟", "让皮肤湿润", "让空气湿润", "让人很凉快"]),
          ("他们正在举办什么活动？", "A", ["免费试用", "买一送一", "半价出售", "九折出售"])]),
        ("我们的任务已经按计划全部完成了。这一段时间，尽管工作压力很大，中间也遇到了许多困难，但是因为有大家的支持，我们能够快速、积极地找到问题的原因，及时地解决问题，保质保量地完成任务。非常感谢大家对我的支持！",
         [("关于这个任务，下列哪个正确？", "B", ["压力不大", "已按时完成", "质量有问题", "完成速度太慢"]),
          ("说话人正在做什么？", "B", ["接受道歉", "感谢同事", "解释原因", "接受任务"])]),
    ]
    for passage, qs in l3_groups:
        plan.append({
            "part": 3,
            "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False, "loi_nghe": passage},
            "children": [[{"dang": "chon_mot", "loi_nghe": q_said, "phuong_an": opts_text(op, ans)}, False] for q_said, ans, op in qs],
        })

    # Part 4: Đọc 46–50 & 51–55 (Điền từ)
    plan.append({
        "part": 4,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(["冷静", "地址", "引起", "坚持", "禁止", "消息"])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "她每天都（　）走路上下班，所以身体一直很不错。", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "他从网站上看到了这个激动人心的（　）。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "这儿写着“（　）停车”，他们只好把车停在那边了。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "喂，告诉我你的（　），我准备给你寄几本书。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "人与人之间如果缺少交流，可能就会（　）误会。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "问题越是复杂时，你越要（　），千万别着急。", "dap_an_thu_tu": 1}, False],
        ],
    })
    plan.append({
        "part": 4,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(["填", "正式", "温度", "酸", "广播", "肚子"])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "A：今天真冷啊，好像白天最高（　）才2℃。\nB：刚才电视里说明天更冷。", "dap_an_thu_tu": 3}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "A：我的（　）在叫了，早上只吃了一小块儿蛋糕。\nB：饿了？我包里有巧克力，给你。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：这两瓶饮料有什么区别吗？\nB：左边这瓶有点儿（　），右边这瓶是甜的。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：快点儿，咱们的飞机就要起飞了。\nB：没事，（　）里说，国际航班都推迟起飞了，咱可以再逛逛。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：最近怎么穿得这么（　）？很精神啊。\nB：我现在开始上班了，这是公司的规定。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：你好，我想办一张信用卡。\nB：好的，先生，请您先（　）一下这张申请表。", "dap_an_thu_tu": 1}, False],
        ],
    })

    # Part 5: Đọc 56–65 (Sắp xếp A, B, C)
    r2 = [
        (True, "BAC", ("可是今天起晚了", "平时我骑自行车上下班", "所以就打车来公司")),
        (False, "ACB", ("做事情往往需要照顾大的方面", "而放弃掉“森林”", "换句话说，就是不要仅仅为了一棵“大树”")),
        (False, "BAC", ("于是大家都以为他是一个骄傲的人", "他从来不主动和别人说话", "其实他只是有点儿害羞")),
        (False, "ABC", ("语法是语言学习中很重要的一部分", "却不是语言学习的全部", "文化在语言学习中也很重要")),
        (False, "ACB", ("选择在电视上做广告", "扩大我们葡萄酒的影响力", "是因为它可以在较短的时间内")),
        (False, "ACB", ("这种树叶宽、厚的绿色植物", "也能给我们带来一个好的心情", "不仅可以使室内空气更新鲜")),
        (False, "CAB", ("就受到人们的普遍欢迎", "当时的人们没想到它会给环境带来严重的污染", "100年前，塑料一出现")),
        (False, "BCA", ("首先要学会像扔垃圾一样把烦恼扔掉", "生活中总会有烦恼", "要想让自己轻松、愉快")),
        (False, "ABC", ("“明”由两个字组成", "左边的“日”代表太阳，而右边的“月”代表月亮", "所以“明”在汉语中表示有光亮的意思")),
        (False, "BAC", ("河水不深，非常清", "我记得，以前村子的旁边有一条小河", "清得可以看见河底的水草和成群的小鱼")),
        (False, "CBA", ("可惜到现在仍然没有一个科学的说法", "有些人甚至专门写过这方面的书", "很多人都曾经试着对梦进行解释")),
    ]
    for ex, order, (a, b, c) in r2:
        by_let = {"A": a, "B": b, "C": c}
        joined = "".join(by_let[ch] for ch in order)
        plan.append({
            "part": 5, "ex": ex,
            "q": {
                "dang": "sap_xep", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                "noi_dung": "Sắp xếp A, B, C thành đoạn văn đúng (gõ thứ tự, ví dụ BAC).",
                "phuong_an": [{"noi_dung": f"A {a}"}, {"noi_dung": f"B {b}"}, {"noi_dung": f"C {c}"}],
                "dap_an_chap_nhan": [order, joined],
            },
        })

    # Part 6: Đọc 66–79 (đơn) + 80–85 (3 đoạn × 2 câu)
    r3_single = [
        (True, "A", ["幽默", "马虎", "骄傲", "害羞"], "她很活泼，说话很有趣，总能给我们带来快乐，我们都很喜欢和她在一起。\n★她是个什么样的人？"),
        (False, "D", ["很危险", "爱喝啤酒", "都很友好", "酒后不能开车"], "司机喝酒后不允许开车。因为无论对自己还是对其他人，这样做都是极其危险的。\n★根据这段话，司机："),
        (False, "A", ["要多听", "要准时", "要多表扬别人", "要严格要求自己"], "最有用的人，不一定是最能说的人。上天给我们两只耳朵、一个嘴，就是让我们多听少说的。学会多听，说明一个人真正成熟了。\n★这段话告诉我们："),
        (False, "D", ["太懒", "很孤单", "爱开玩笑", "不会管理时间"], "孩子从小就要养成管理自己的好习惯。管理自己不但指自己的事情自己做，更重要的是时间管理，让孩子会计划自己的时间，今天应该完成的事情就不能留到明天，不要总说“来不及了”。\n★为什么有的孩子总说“来不及了”？"),
        (False, "C", ["不打折", "特别软", "样子很流行", "质量不合格"], "您看这个沙发怎么样？我们年底有活动，正在打折，比平时便宜了一千块。不过您放心，质量肯定不“打折”，这种沙发是今年最流行的，有很多种颜色可以选择，您可以考虑一下。\n★这种沙发："),
        (False, "D", ["讨厌约会", "喜欢玩电脑", "会找我聊天", "会去唱歌跳舞"], "当我觉得累的时候，我就找一个安静的地方，一边喝茶一边听音乐。弟弟正好和我相反，这种时候，他喜欢去热闹的地方，和别人一起唱歌、跳舞。\n★弟弟累的时候："),
        (False, "B", ["生命", "感情", "动作", "感觉"], "只有动作没有感情的表演是没有生命力的，一个好的演员，想要拉近和观众的距离，就要学会用感情和观众进行对话与交流。\n★表演要具有生命力，应该重视什么？"),
        (False, "D", ["顾客不多", "只卖羊肉汤", "在全国很有名", "有半个世纪了"], "这是一家在当地非常有名的面馆儿，历史已经超过50年了。它一直只卖一种东西：牛肉面。由于面的味道很特别，在众多食客中名气很大。\n★这家面馆儿："),
        (False, "D", ["生病了", "走错门了", "工作太忙", "忘拿钥匙了"], "晚上，我刚刚躺下，就响起了敲门声。一猜就知道是和我一起租房的那个人又没带钥匙。他好像特别马虎，虽然每次都红着脸向我说抱歉、打扰了，可过不了几天，就又能听到他的敲门声了。\n★敲门的那个人怎么了？"),
        (False, "C", ["很无聊", "让人难受", "不是可怜", "是暂时的"], "同情是最美好的情感之一，然而同情并不是高高在上的关心，它应该是对别人经历的情感的理解、尊重和支持。\n★这段话认为，同情："),
        (False, "B", ["想鼓励他", "他过生日", "春节快到了", "要去海洋馆"], "猜猜我奶奶给了我什么生日礼物？一个照相机！正好明天去海洋馆，我来给你们照相吧。\n★奶奶给孙子买照相机，是因为："),
        (False, "A", ["16", "17", "18", "19"], "这座楼一共有28层，为了节约您的时间，3号、4号电梯17层以下不停，直接到17-28层，如果您要到1-16层，请乘坐西边的1号和2号电梯。\n★1号电梯可以去哪层？"),
        (False, "C", ["参观", "吃饭", "看京剧", "参加演出"], "我姓李，是各位的导游。这是大家的护照和房卡，放下行李后请到这里集合，我们一会儿去吃饭。晚上有京剧，座位要提前联系，想看的现在报名。\n★导游让大家报名去："),
        (False, "B", ["收入减少", "发展很快", "主要制造家具", "不适应市场变化"], "经过他的努力，公司的生意越做越大，最近又在三个城市开了新的分公司。一切都在往好的方向发展，他也更有信心了。\n★公司现在怎么样？"),
        (False, "C", ["仔细", "认真", "失败", "准确的判断"], "我们对失败应该有正确的认识。偶尔的失败其实可以让我们清楚自己还有什么地方需要提高，这可以帮助我们走向最后的成功。\n★“这”指的是："),
    ]
    for ex, ans, op, s in r3_single:
        plan.append({
            "part": 6, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "phuong_an": opts_text(op, ans)},
        })

    r3_groups = [
        ("年轻人刚刚进入社会的时候，不要太急着赚钱，不要眼睛里只有工资和奖金。实际上，正确的做法应该是，在工作的前几年，重点要丰富自己的工作经验，学习与同事们交流的方法，积累专业的知识和技术，还有，要懂得什么是职业的态度等。这些比收入重要多了。",
         [("★什么更重要？", "A", ["经验", "友谊", "标准", "过程"]),
          ("★这段话主要提醒刚进入社会的年轻人：", "A", ["要有耐心", "要信任别人", "人都有缺点", "不要怀疑自己"])]),
        ("《富爸爸，穷爸爸》讲了这样一个故事，作者的父亲和朋友的父亲对金钱的看法完全不同，这使他对金钱有了兴趣，最终，他接受了朋友的父亲的看法，也就是书中所说的“富爸爸”的看法：人们不应该为钱工作，而要让钱为我们工作。",
         [("★这本书中的穷爸爸是指：", "C", ["金钱", "工作", "作者的爸爸", "朋友的爸爸"]),
          ("★富爸爸对金钱的看法是：", "D", ["先赚再花", "钱并不重要", "钱让人快乐", "让钱为我们服务"])]),
        ("中国南北距离约5500公里，因此南北气候有很大区别。南方很多地方的冬天一点儿也不冷，温度跟北方春天差不多，2月份的时候已经很暖和，可以只穿一件毛衣了，树开始长出新叶子，路边的花也开了，非常漂亮。所以很多北方人都喜欢这个时候出发去南方旅游。不过可惜的是，南方很多地方冬天都看不到雪，孩子们少了玩雪的快乐。",
         [("★南方很多地方，2月：", "A", ["树变绿了", "都是晴天", "逐渐变冷", "会突然下雪"]),
          ("★这段话主要介绍什么？", "C", ["2月的天气", "南北的不同", "南方的冬天", "南方的风景"])]),
    ]
    for passage, qs in r3_groups:
        plan.append({
            "part": 6,
            "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False, "noi_dung": passage},
            "children": [[{"dang": "chon_mot", "noi_dung": q_s, "phuong_an": opts_text(op, ans)}, False] for q_s, ans, op in qs],
        })

    # Part 7: Viết 86–95 (Sắp xếp từ thành câu)
    w1 = [
        (True, ["那座桥", "800年的", "历史", "有", "了"], ["那座桥有800年的历史了。"]),
        (False, ["好处", "抽烟", "对身体", "没有"], ["抽烟对身体没有好处。"]),
        (False, ["我", "陪叔叔", "去长城", "看看", "打算"], ["我打算陪叔叔去长城看看。"]),
        (False, ["个", "又脏又破", "那", "白色的盒子"], ["那个白色的盒子又脏又破。"]),
        (False, ["妹妹", "弹钢琴的声音", "吵醒了", "把爷爷"], ["妹妹弹钢琴的声音把爷爷吵醒了。"]),
        (False, ["语言表达能力", "经常阅读报纸", "提高", "能"], ["经常阅读报纸能提高语言表达能力。"]),
        (False, ["举行", "这次电影艺术节", "在北京", "也许", "会"], ["这次电影艺术节也许会在北京举行。", "也许这次电影艺术节会在北京举行。"]),
        (False, ["整理", "儿子的复习笔记", "得", "很详细"], ["儿子的复习笔记整理得很详细。"]),
        (False, ["请假休息", "重感冒", "让他", "不得不"], ["重感冒让他不得不请假休息。"]),
        (False, ["范围", "他说的问题", "今天讨论的", "超出了"], ["他说的问题超出了今天讨论的范围。"]),
        (False, ["告诉他", "答案", "你", "最好", "别"], ["你最好别告诉他答案。"]),
    ]
    for ex, pieces, acc in w1:
        plan.append({
            "part": 7, "ex": ex,
            "q": {"dang": "sap_xep", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": "完成句子。", "phuong_an": [{"noi_dung": p} for p in pieces], "dap_an_chap_nhan": acc},
        })

    # Part 8: Viết 96–100 (Nhìn tranh dùng từ đặt câu)
    w2 = [
        (True, 0, "乒乓球", "她很喜欢打乒乓球。"),
        (False, 1, "吃惊", "她听了以后很吃惊。"),
        (False, 2, "汗", "她出了许多汗。"),
        (False, 3, "挂", "他想把画挂在墙上。"),
        (False, 4, "香", "这些花闻起来很香。"),
        (False, 5, "杂志", "他坐在沙发上看杂志。"),
    ]
    for ex, pic_idx, word, sample in w2:
        plan.append({
            "part": 8, "ex": ex,
            "q": {
                "dang": "viet_mo", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                "noi_dung": "看图，用词造句。",
                "tep_hinh": img(pic_idx),
                "tu_bat_buoc": word,
                "tieu_chi_mo_ta": "Viết một câu hoàn chỉnh, đúng ngữ pháp, có dùng từ cho sẵn và phù hợp với nội dung hình.",
                "diem_toi_da": 10,
                "nguong_dat": 6,
                "giai_thich": f"Câu tham khảo trong đáp án đề: {sample}",
            },
        })

    return {
        "exam": {
            "code": "H41002",
            "level": "HSK4",
            "ten": "HSK 4 – Đề 2",
            "phut": 105,
            "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（四级）H41002",
            "audio": f"exams/{slug}/listening.mp3",
            "img_dir": f"exams/{slug}/img",
        },
        "plan": plan,
    }


def import_exam_data(db, lecturer_id: int, data: dict) -> None:
    exam = data["exam"]
    if db.execute(text("SELECT 1 FROM bo_de WHERE ma_de = :m"), {"m": exam["code"]}).first():
        print(f"· Bỏ qua {exam['ten']} ({exam['code']}): đã tồn tại")
        return

    level = int(db.execute(text("SELECT id FROM cap_do WHERE ma = :m"), {"m": exam["level"]}).scalar_one())

    # Validate media
    paths = [exam["audio"]]
    for entry in data["plan"]:
        objs = [entry.get("q") or entry.get("group")] + [c for c, _ in entry.get("children", [])]
        for obj in objs:
            paths += [obj.get("tep_hinh")] + [o.get("tep_hinh") for o in obj.get("phuong_an", [])]
    missing = sorted({p for p in paths if p and not (UPLOADS / p).is_file()})
    if missing:
        raise RuntimeError(f"Thiếu tệp media cho {exam['code']}: {missing[:5]}")

    # Validate all QuestionIn payloads before writing to DB
    prepared = []
    for idx, entry in enumerate(data["plan"], start=1):
        if "group" in entry:
            body = {**entry["group"], "cap_do_id": level, "cau_con": [c for c, _ in entry["children"]]}
            flags = [bool(ex) for _, ex in entry["children"]]
        else:
            body = {**entry["q"], "cap_do_id": level}
            flags = bool(entry.get("ex"))
        q_in = QuestionIn(**body)
        validate_question(q_in)
        prepared.append((entry["part"], q_in, flags))

    items: list[ExamItemIn] = []
    for part, q_in, flags in prepared:
        qid = create_question(db, q_in, lecturer_id)
        publish_question(db, qid, lecturer_id)
        if isinstance(flags, list):
            child_ids = [int(r[0]) for r in db.execute(
                text("SELECT id FROM cau_hoi WHERE cau_cha_id = :p ORDER BY id"), {"p": qid}
            ).all()]
            items += [ExamItemIn(cau_hoi_id=c, phan=part, la_cau_vi_du=ex) for c, ex in zip(child_ids, flags)]
        else:
            items.append(ExamItemIn(cau_hoi_id=qid, phan=part, la_cau_vi_du=flags))

    exam_id = exam_service.create_exam(db, ExamInfoIn(
        cap_do_id=level,
        ten=exam["ten"],
        ma_de=exam["code"],
        thoi_luong_phut=exam["phut"],
        nguon=exam["nguon"],
        tep_audio_chung=exam["audio"],
    ), lecturer_id)
    exam_service.set_exam_items(db, exam_id, items)
    exam_service.publish_exam(db, exam_id)
    scored = sum(1 for i in items if not i.la_cau_vi_du)
    print(f"→ Đã nạp & đăng {exam['ten']} ({exam['code']}): {scored} câu tính điểm, {len(items) - scored} câu ví dụ.")


def main() -> int:
    specs = [
        ("hsk2_h20902.json", build_h20902()),
        ("hsk3_h31002.json", build_h31002()),
        ("hsk4_h41002.json", build_h41002()),
    ]
    for fname, payload in specs:
        (DATA_DIR / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Đã lưu tệp JSON chuẩn: scripts/data/{fname}")

    db = SessionLocal()
    try:
        lecturer_id = int(db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one())
        for _, payload in specs:
            import_exam_data(db, lecturer_id, payload)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
