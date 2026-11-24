"""Biên soạn và nạp 6 đề thi mô phỏng chuẩn cấu trúc HSK 2.0 cho cấp HSK 1:
HSK 1 – Đề 5 (H1M05) .. HSK 1 – Đề 10 (H1M10).

Mỗi đề gồm đúng 40 câu tính điểm (20 Nghe phần 1–4 + 20 Đọc phần 5–8) + 9 câu ví dụ chuẩn Hanban,
có đầy đủ Pinyin, hình ảnh khớp nghĩa 100% và 1 tệp MP3 băng nghe liên tục đa giọng đọc Mandarin.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._sim_exam_helper import LETTER, opts_paths, opts_text, save_and_seed_exams, tf

P0 = lambda n: f"exams/hsk1_h10000/img/{n:03d}.jpg"
P1 = lambda n: f"exams/hsk1_h10901/img/{n:03d}.jpg"
P2 = lambda n: f"exams/hsk1_h10902/img/{n:03d}.jpg"
P3 = lambda n: f"exams/hsk1_h11003/img/{n:03d}.jpg"


def make_hsk1_exam(cfg: dict) -> tuple[str, dict]:
    code = cfg["code"]
    slug = f"hsk1_{code.lower()}"
    plan: list[dict] = []

    # Part 1: Nghe 1–5 (2 câu ví dụ + 5 câu tính điểm)
    l1_full = [
        (True, P0(0), True, "很 高兴", "hěn gāoxìng"),
        (True, P0(1), False, "看 电影", "kàn diànyǐng"),
        *[(False, *row) for row in cfg["L1"]],
    ]
    for ex, pic, ok, said, py in l1_full:
        plan.append({
            "part": 1, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "tep_hinh": pic, "loi_nghe": said, "pinyin": py, "phuong_an": tf(ok)},
        })

    # Part 2: Nghe 6–10 (1 câu ví dụ + 5 câu tính điểm, chọn 1 trong 3 hình)
    l2_full = [
        (True, [P0(7), P0(8), P0(9)], "A", "这 是 我 的 书。", "Zhè shì wǒ de shū."),
        *[(False, *row) for row in cfg["L2"]],
    ]
    for ex, pics3, ans, said, py in l2_full:
        plan.append({
            "part": 2, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "pinyin": py, "phuong_an": opts_paths(pics3, ans)},
        })

    # Part 3: Nghe 11–15 (6 hình A–F dùng chung; C = P0(27) làm câu ví dụ)
    p3_pics = cfg["L3_PICS"]  # 6 paths, index 2 (C) = P0(27)
    p3_children = [
        [{"dang": "chon_bo_chung", "loi_nghe": "女：你 好！\n男：你 好！ 很 高兴 认识 你。",
          "pinyin": "Nǚ: Nǐ hǎo!\nNán: Nǐ hǎo! Hěn gāoxìng rènshi nǐ.", "dap_an_thu_tu": 3}, True],
    ]
    for ans, said, py in cfg["L3"]:
        p3_children.append([{"dang": "chon_bo_chung", "loi_nghe": said, "pinyin": py, "dap_an_thu_tu": LETTER[ans]}, False])
    plan.append({
        "part": 3,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_paths(p3_pics)},
        "children": p3_children,
    })

    # Part 4: Nghe 16–20 (1 câu ví dụ + 5 câu tính điểm)
    l4_full = [
        (True, ["商店 [shāngdiàn]", "医院 [yīyuàn]", "学校 [xuéxiào]"], "A",
         "下午 我 去 商店， 我 想 买 一些 水果。\n问：她 下午 去 哪里？",
         "Xiàwǔ wǒ qù shāngdiàn, wǒ xiǎng mǎi yìxiē shuǐguǒ.\nWèn: Tā xiàwǔ qù nǎlǐ?"),
        *[(False, *row) for row in cfg["L4"]],
    ]
    for ex, opts, ans, said, py in l4_full:
        plan.append({
            "part": 4, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "pinyin": py, "phuong_an": opts_text(opts, ans)},
        })

    # Part 5: Đọc 21–25 (2 câu ví dụ + 5 câu tính điểm: hình + từ Đúng/Sai)
    r1_full = [
        (True, P0(31), "电视", "diànshì", False),
        (True, P0(32), "飞机", "fēijī", True),
        *[(False, *row) for row in cfg["R1"]],
    ]
    for ex, pic, word, py, ok in r1_full:
        plan.append({
            "part": 5, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "tep_hinh": pic, "noi_dung": word, "pinyin": py, "phuong_an": tf(ok)},
        })

    # Part 6: Đọc 26–30 (6 hình A–F dùng chung; E = P0(42) làm câu ví dụ)
    r2_pics = cfg["R2_PICS"]  # index 4 (E) = P0(42)
    r2_children = [
        [{"dang": "chon_bo_chung", "noi_dung": "我 很 喜欢 这 本 书。",
          "pinyin": "Wǒ hěn xǐhuan zhè běn shū.", "dap_an_thu_tu": 5}, True],
    ]
    for ans, s, py in cfg["R2"]:
        r2_children.append([{"dang": "chon_bo_chung", "noi_dung": s, "pinyin": py, "dap_an_thu_tu": LETTER[ans]}, False])
    plan.append({
        "part": 6,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_paths(r2_pics)},
        "children": r2_children,
    })

    # Part 7: Đọc 31–35 (Ghép câu hỏi – đáp A–F; F làm ví dụ)
    r3_children = [
        [{"dang": "chon_bo_chung", "noi_dung": "你 喝 水 吗？", "pinyin": "Nǐ hē shuǐ ma?", "dap_an_thu_tu": 6}, True],
    ]
    for ans, s, py in cfg["R3"]:
        r3_children.append([{"dang": "chon_bo_chung", "noi_dung": s, "pinyin": py, "dap_an_thu_tu": LETTER[ans]}, False])
    plan.append({
        "part": 7,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(cfg["R3_OPTS"])},
        "children": r3_children,
    })

    # Part 8: Đọc 36–40 (Điền từ A–F; D = 名字 [míngzi] làm ví dụ)
    r4_children = [
        [{"dang": "chon_bo_chung", "noi_dung": "你 叫 什么 （　）？", "pinyin": "Nǐ jiào shénme ( )?", "dap_an_thu_tu": 4}, True],
    ]
    for ans, s, py in cfg["R4"]:
        r4_children.append([{"dang": "chon_bo_chung", "noi_dung": s, "pinyin": py, "dap_an_thu_tu": LETTER[ans]}, False])
    plan.append({
        "part": 8,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(cfg["R4_OPTS"])},
        "children": r4_children,
    })

    return f"{slug}.json", {
        "exam": {
            "code": code,
            "level": "HSK1",
            "ten": cfg["ten"],
            "phut": 40,
            "nguon": "Đề mô phỏng biên soạn chuẩn cấu trúc HSK 2.0 (HSK 一级)",
            "audio": f"exams/{slug}/listening.mp3",
        },
        "plan": plan,
    }


HSK1_CONFIGS = [
    # ==================== ĐỀ 5 (H1M05) ====================
    {
        "code": "H1M05",
        "ten": "HSK 1 – Đề 5",
        "L1": [
            (P2(3), True, "她 在 喝 水。", "Tā zài hē shuǐ."),
            (P3(13), False, "桌子上 有 一 个 电脑。", "Zhuōzi shang yǒu yí ge diànnǎo."),
            (P1(13), True, "现在 是 十 点 十 分。", "Xiànzài shì shí diǎn shí fēn."),
            (P2(11), False, "我 喜欢 吃 苹果。", "Wǒ xǐhuan chī píngguǒ."),
            (P0(41), True, "他 是 医院 的 医生。", "Tā shì yīyuàn de yīshēng."),
        ],
        "L2": [
            ([P3(40), P3(12), P3(25)], "B", "妈妈 很 会 做 菜。", "Māma hěn huì zuò cài."),
            ([P1(13), P1(14), P3(36)], "C", "我 上午 九 点 去 学校。", "Wǒ shàngwǔ jiǔ diǎn qù xuéxiào."),
            ([P1(28), P1(37), P0(32)], "A", "我 家 的 小 猫 在 椅子 上。", "Wǒ jiā de xiǎo māo zài yǐzi shang."),
            ([P1(6), P2(22), P3(2)], "A", "今天 外面 下 雨 了。", "Jīntiān wàimiàn xià yǔ le."),
            ([P0(40), P0(29), P0(32)], "C", "爸爸 明天 坐 飞机 去 北京。", "Bàba míngtiān zuò fēijī qù Běijīng."),
        ],
        "L3_PICS": [P2(6), P3(43), P0(27), P3(4), P1(2), P0(43)],
        "L3": [
            ("A", "女：请 坐， 你 喝 茶 吗？\n男：好 的， 谢谢 你。", "Nǚ: Qǐng zuò, nǐ hē chá ma?\nNán: Hǎo de, xièxie nǐ."),
            ("E", "男：喂， 李 老师 在 吗？\n女：她 不 在， 她 去 学校 了。", "Nán: Wéi, Lǐ lǎoshī zài ma?\nNǚ: Tā bú zài, tā qù xuéxiào le."),
            ("B", "男：你们 下午 去 哪儿 了？\n女：我们 去 商店 买 衣服 了。", "Nán: Nǐmen xiàwǔ qù nǎr le?\nNǚ: Wǒmen qù shāngdiàn mǎi yīfu le."),
            ("D", "女：儿子 在 做 什么 呢？\n男：他 和 爸爸 在 看 书 呢。", "Nǚ: Érzi zài zuò shénme ne?\nNán: Tā hé bàba zài kàn shū ne."),
            ("F", "女：张 先生 呢？\n男：他 太 累 了， 在 里面 睡觉 呢。", "Nǚ: Zhāng xiānsheng ne?\nNán: Tā tài lèi le, zài lǐmiàn shuìjiào ne."),
        ],
        "L4": [
            (["星期二 [xīngqī'èr]", "星期四 [xīngqīsì]", "星期六 [xīngqīliù]"], "B",
             "今天 星期三， 明天 我 去 看 同学。\n问：他 哪 天 去 看 同学？",
             "Jīntiān xīngqīsān, míngtiān wǒ qù kàn tóngxué.\nWèn: Tā nǎ tiān qù kàn tóngxué?"),
            (["12 块 [12 kuài]", "20 块 [20 kuài]", "30 块 [30 kuài]"], "A",
             "这 本 汉语 书 十二 块 钱。\n问：这 本 书 多少 钱？",
             "Zhè běn Hànyǔ shū shí'èr kuài qián.\nWèn: Zhè běn shū duōshao qián?"),
            (["医院 [yīyuàn]", "饭馆儿 [fànguǎnr]", "火车站 [huǒchēzhàn]"], "B",
             "中午 我们 去 学校 前面 的 饭馆儿 吃 米饭。\n问：他们 中午 去 哪儿？",
             "Zhōngwǔ wǒmen qù xuéxiào qiánmiàn de fànguǎnr chī mǐfàn.\nWèn: Tāmen zhōngwǔ qù nǎr?"),
            (["女儿 [nǚ'ér]", "妈妈 [māma]", "老师 [lǎoshī]"], "A",
             "王 先生 的 女儿 今年 八 岁， 很 喜欢 读 书。\n问：谁 今年 八 岁？",
             "Wáng xiānsheng de nǚ'ér jīnnián bā suì, hěn xǐhuan dú shū.\nWèn: Shéi jīnnián bā suì?"),
            (["出租车 [chūzūchē]", "飞机 [fēijī]", "火车 [huǒchē]"], "C",
             "我 明天 上午 九 点 坐 火车 回 家。\n问：他 怎么 回 家？",
             "Wǒ míngtiān shàngwǔ jiǔ diǎn zuò huǒchē huí jiā.\nWèn: Tā zěnme huí jiā?"),
        ],
        "R1": [
            (P3(3), "杯子", "bēizi", True),
            (P2(37), "桌子", "zhuōzi", False),
            (P0(33), "小狗", "xiǎogǒu", True),
            (P1(33), "睡觉", "shuìjiào", False),
            (P0(35), "水果", "shuǐguǒ", True),
        ],
        "R2_PICS": [P0(17), P3(20), P2(29), P3(40), P0(42), P1(25)],
        "R2": [
            ("D", "我 和 妈妈 周末 去 看 电影。", "Wǒ hé māma zhōumò qù kàn diànyǐng."),
            ("A", "她 是 我们 学校 的 汉语 老师。", "Tā shì wǒmen xuéxiào de Hànyǔ lǎoshī."),
            ("B", "姐姐 会 开 车， 她 开 车 去 工作。", "Jiějie huì kāi chē, tā kāi chē qù gōngzuò."),
            ("C", "这些 水果 很 好， 你 吃 一 个 吧。", "Zhèxiē shuǐguǒ hěn hǎo, nǐ chī yí ge ba."),
            ("F", "我们 住 在 一零二， 欢迎 你 来。", "Wǒmen zhù zài yīlíng'èr, huānyíng nǐ lái."),
        ],
        "R3_OPTS": [
            "三 个 人。 [Sān ge rén.]",
            "在 桌子 上。 [Zài zhuōzi shang.]",
            "不 客气。 [Bú kèqi.]",
            "十 月 五 号。 [Shí yuè wǔ hào.]",
            "会 写 一些。 [Huì xiě yìxiē.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            ("B", "我 的 小 杯子 在 哪儿？", "Wǒ de xiǎo bēizi zài nǎr?"),
            ("A", "你 家 有 几 个 人？", "Nǐ jiā yǒu jǐ ge rén?"),
            ("E", "你 会 写 汉字 吗？", "Nǐ huì xiě Hànzì ma?"),
            ("C", "谢谢 你 请 我 喝 茶！", "Xièxie nǐ qǐng wǒ hē chá!"),
            ("D", "今天 是 几 月 几 号？", "Jīntiān shì jǐ yuè jǐ hào?"),
        ],
        "R4_OPTS": [
            "漂亮 [piàoliang]", "认识 [rènshi]", "冷 [lěng]", "名字 [míngzi]", "多少 [duōshao]", "回 [huí]",
        ],
        "R4": [
            ("E", "小姐， 这个 衣服 （　） 钱？", "Xiǎojiě, zhège yīfu ( ) qián?"),
            ("C", "今天 北京 的 天气 很 （　）。", "Jīntiān Běijīng de tiānqì hěn ( )."),
            ("F", "下午 五 点 我 和 朋友 一起 （　） 家。", "Xiàwǔ wǔ diǎn wǒ hé péngyou yìqǐ ( ) jiā."),
            ("A", "你 女儿 的 这 件 衣服 很 （　）。", "Nǐ nǚ'ér de zhè jiàn yīfu hěn ( )."),
            ("B", "男：很 高兴 （　） 你！\n女：我 也 很 高兴。", "Nán: Hěn gāoxìng ( ) nǐ!\nNǚ: Wǒ yě hěn gāoxìng."),
        ],
    },

    # ==================== ĐỀ 6 (H1M06) ====================
    {
        "code": "H1M06",
        "ten": "HSK 1 – Đề 6",
        "L1": [
            (P1(5), True, "她 在 喝 牛奶。", "Tā zài hē niúnǎi."),
            (P0(29), False, "他 明天 坐 火车 去。", "Tā míngtiān zuò huǒchē qù."),
            (P3(25), True, "她 写 的 汉字 很 漂亮。", "Tā xiě de Hànzì hěn piàoliang."),
            (P1(10), True, "今天 天气 太 冷 了。", "Jīntiān tiānqì tài lěng le."),
            (P2(4), False, "他们 在 商店 买 东西。", "Tāmen zài shāngdiàn mǎi dōngxi."),
        ],
        "L2": [
            ([P0(37), P2(11), P0(9)], "B", "中午 我 想 吃 一 碗 米饭。", "Zhōngwǔ wǒ xiǎng chī yì wǎn mǐfàn."),
            ([P1(34), P1(2), P3(26)], "A", "姐姐 喜欢 在 家 听 音乐。", "Jiějie xǐhuan zài jiā tīng yīnyuè."),
            ([P0(4), P1(14), P1(15)], "A", "现在 中午 十二 点 了， 我们 去 吃 饭 吧。", "Xiànzài zhōngwǔ shí'èr diǎn le, wǒmen qù chī fàn ba."),
            ([P0(28), P0(31), P3(13)], "B", "爸爸 给 我 买 了 一 个 新 电脑。", "Bàba gěi wǒ mǎile yí ge xīn diànnǎo."),
            ([P3(18), P0(17), P0(16)], "A", "王 小姐 在 医院 工作， 是 医生。", "Wáng xiǎojiě zài yīyuàn gōngzuò, shì yīshēng."),
        ],
        "L3_PICS": [P1(26), P2(28), P0(27), P3(30), P2(17), P1(24)],
        "L3": [
            ("E", "女：爸爸 在 哪儿 呢？\n男：他 在 厨房 做 饭 呢。", "Nǚ: Bàba zài nǎr ne?\nNán: Tā zài chúfáng zuò fàn ne."),
            ("B", "男：这 只 大 狗 是 你 家 的 吗？\n女：是， 我 儿子 很 喜欢 它。", "Nán: Zhè zhī dà gǒu shì nǐ jiā de ma?\nNǚ: Shì, wǒ érzi hěn xǐhuan tā."),
            ("A", "女：这个 杯子 很 好， 你 买 吗？\n男：对不起， 我 今天 没 钱 了。", "Nǚ: Zhège bēizi hěn hǎo, nǐ mǎi ma?\nNán: Duìbuqǐ, wǒ jīntiān méi qián le."),
            ("F", "男：下 个 月 你 想 去 哪儿？\n女：我 想 和 朋友 去 中国 北京。", "Nán: Xià ge yuè nǐ xiǎng qù nǎr?\nNǚ: Wǒ xiǎng hé péngyou qù Zhōngguó Běijīng."),
            ("D", "女：再见， 明天 学校 见！\n男：好 的， 再见！", "Nǚ: Zàijiàn, míngtiān xuéxiào jiàn!\nNán: Hǎo de, zàijiàn!"),
        ],
        "L4": [
            (["3 个 [3 ge]", "5 个 [5 ge]", "8 个 [8 ge]"], "B",
             "桌子 上 有 五 个 大 苹果。\n问：桌子 上 有 几 个 苹果？",
             "Zhuōzi shang yǒu wǔ ge dà píngguǒ.\nWèn: Zhuōzi shang yǒu jǐ ge píngguǒ?"),
            (["中国人 [Zhōngguórén]", "老师 [lǎoshī]", "学生 [xuésheng]"], "C",
             "他 今年 二十 岁， 在 北京 大学 学习 汉语。\n问：他 是 做 什么 的？",
             "Tā jīnnián èrshí suì, zài Běijīng Dàxué xuéxí Hànyǔ.\nWèn: Tā shì zuò shénme de?"),
            (["椅子 下 [yǐzi xià]", "电脑 后面 [diànnǎo hòumiàn]", "商店 里 [shāngdiàn li]"], "B",
             "你 的 茶杯 在 电脑 后面 呢。\n问：茶杯 在 哪儿？",
             "Nǐ de chábēi zài diànnǎo hòumiàn ne.\nWèn: Chábēi zài nǎr?"),
            (["很 热 [hěn rè]", "下 雨 了 [xià yǔ le]", "很 好 [hěn hǎo]"], "A",
             "今天 太 热 了， 我 不 想 出去， 想 在 家 吃 西瓜。\n问：今天 天气 怎么样？",
             "Jīntiān tài rè le, wǒ bù xiǎng chūqù, xiǎng zài jiā chī xīguā.\nWèn: Jīntiān tiānqì zěnmeyàng?"),
            (["上午 [shàngwǔ]", "中午 [zhōngwǔ]", "下午 [xiàwǔ]"], "C",
             "李 先生 上午 不 在 家， 下午 三 点 回来。\n问：李 先生 什么 时候 回来？",
             "Lǐ xiānsheng shàngwǔ bú zài jiā, xiàwǔ sān diǎn huílai.\nWèn: Lǐ xiānsheng shénme shíhou huílai?"),
        ],
        "R1": [
            (P0(9), "苹果", "píngguǒ", True),
            (P3(37), "工作", "gōngzuò", False),
            (P0(40), "火车", "huǒchē", True),
            (P1(28), "小狗", "xiǎogǒu", False),
            (P3(41), "请坐", "qǐng zuò", True),
        ],
        "R2_PICS": [P1(39), P2(43), P0(15), P3(24), P0(42), P0(30)],
        "R2": [
            ("C", "他们 两 个 人 都 在 公司 工作。", "Tāmen liǎng ge rén dōu zài gōngsī gōngzuò."),
            ("A", "喂， 妈妈， 我 下午 六 点 回 家。", "Wéi, māma, wǒ xiàwǔ liù diǎn huí jiā."),
            ("D", "儿子 的 这 件 衣服 太 小 了。", "Érzi de zhè jiàn yīfu tài xiǎo le."),
            ("F", "她们 三 个 人 是 好 同学。", "Tāmen sān ge rén shì hǎo tóngxué."),
            ("B", "妈妈， 这个 菜 很 好吃。", "Māma, zhège cài hěn hǎochī."),
        ],
        "R3_OPTS": [
            "没 关系。 [Méi guānxi.]",
            "我 爸爸 的。 [Wǒ bàba de.]",
            "八 点 十 分。 [Bā diǎn shí fēn.]",
            "在 医院 工作。 [Zài yīyuàn gōngzuò.]",
            "坐 出租车 去。 [Zuò chūzūchē qù.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            ("E", "我们 怎么 去 火车站？", "Wǒmen zěnme qù huǒchēzhàn?"),
            ("A", "对不起， 我 不 会 说 汉语。", "Duìbuqǐ, wǒ bú huì shuō Hànyǔ."),
            ("B", "桌子 上 的 电脑 是 谁 的？", "Zhuōzi shang de diànnǎo shì shéi de?"),
            ("C", "现在 几 点 了？", "Xiànzài jǐ diǎn le?"),
            ("D", "你 姐姐 在 哪儿 工作？", "Nǐ jiějie zài nǎr gōngzuò?"),
        ],
        "R4_OPTS": [
            "喜欢 [xǐhuan]", "听 [tīng]", "星期 [xīngqī]", "名字 [míngzi]", "朋友 [péngyou]", "住 [zhù]",
        ],
        "R4": [
            ("F", "张 老师 在 北京 （　） 了 六 年 了。", "Zhāng lǎoshī zài Běijīng ( ) le liù nián le."),
            ("A", "我 儿子 最 （　） 吃 中国 菜。", "Wǒ érzi zuì ( ) chī Zhōngguó cài."),
            ("E", "他 是 我 在 大学 认识 的 好 （　）。", "Tā shì wǒ zài dàxué rènshi de hǎo ( )."),
            ("C", "一 个 （　） 有 七 天。", "Yí ge ( ) yǒu qī tiān."),
            ("B", "女：请 大 家 （　） 我 读 这个 汉字。\n男：好 的， 老师。", "Nǚ: Qǐng dàjiā ( ) wǒ dú zhège Hànzì.\nNán: Hǎo de, lǎoshī."),
        ],
    },

    # ==================== ĐỀ 7 (H1M07) ====================
    {
        "code": "H1M07",
        "ten": "HSK 1 – Đề 7",
        "L1": [
            (P0(5), True, "她 喜欢 吃 西瓜。", "Tā xǐhuan chī xīguā."),
            (P1(15), False, "现在 九 点 了。", "Xiànzài jiǔ diǎn le."),
            (P3(6), True, "学生们 在 学校 学习 呢。", "Xuéshengmen zài xuéxiào xuéxí ne."),
            (P0(34), True, "这 件 红色 的 衣服 很 好看。", "Zhè jiàn hóngsè de yīfu hěn hǎokàn."),
            (P1(30), False, "他们 在 饭馆儿 吃 午饭。", "Tāmen zài fànguǎnr chī wǔfàn."),
        ],
        "L2": [
            ([P0(39), P2(33), P2(3)], "A", "请 喝 一 杯 热 茶 吧。", "Qǐng hē yì bēi rè chá ba."),
            ([P2(20), P2(19), P3(38)], "A", "椅子 上 有 一 个 苹果。", "Yǐzi shang yǒu yí ge píngguǒ."),
            ([P0(24), P2(36), P1(34)], "B", "中午 她 在 桌子 上 睡觉 呢。", "Zhōngwǔ tā zài zhuōzi shang shuìjiào ne."),
            ([P2(41), P1(6), P3(2)], "A", "今天 天气 太 热 了！", "Jīntiān tiānqì tài rè le!"),
            ([P0(26), P0(17), P0(41)], "A", "姐姐 上午 去 商店 买 了 不少 东西。", "Jiějie shàngwǔ qù shāngdiàn mǎile bù shǎo dōngxi."),
        ],
        "L3_PICS": [P1(38), P0(25), P0(27), P2(40), P1(29), P3(28)],
        "L3": [
            ("B", "女：中午 我们 吃 什么？\n男：我 做 了 你 爱 吃 的 中国 菜。", "Nǚ: Zhōngwǔ wǒmen chī shénme?\nNán: Wǒ zuòle nǐ ài chī de Zhōngguó cài."),
            ("E", "男：请问， 这个 字 怎么 读？\n女：这个 字 读 “好”。", "Nán: Qǐngwèn, zhège zì zěnme dú?\nNǚ: Zhège zì dú “hǎo”."),
            ("A", "女：今天 是 你 的 生日， 这 是 给 你 的。\n男：太 高兴 了， 谢谢 你！", "Nǚ: Jīntiān shì nǐ de shēngrì, zhè shì gěi nǐ de.\nNán: Tài gāoxìng le, xièxie nǐ!"),
            ("D", "女：喂， 你 到 机场 了 吗？\n男：到 了， 我 下午 三 点 的 飞机。", "Nǚ: Wéi, nǐ dào jīchǎng le ma?\nNán: Dào le, wǒ xiàwǔ sān diǎn de fēijī."),
            ("F", "男：这 一 块 钱 是 谁 的？\n女：是 我 弟弟 的， 谢谢。", "Nán: Zhè yí kuài qián shì shéi de?\nNǚ: Shì wǒ dìdi de, xièxie."),
        ],
        "L4": [
            (["妈妈 [māma]", "爸爸 [bàba]", "哥哥 [gēge]"], "B",
             "我 妈妈 是 老师， 我 爸爸 是 医生。\n问：谁 是 医生？",
             "Wǒ māma shì lǎoshī, wǒ bàba shì yīshēng.\nWèn: Shéi shì yīshēng?"),
            (["6 月 [6 yuè]", "9 月 [9 yuè]", "11 月 [11 yuè]"], "B",
             "我 九 月 去 北京 大学 读 书。\n问：她 几 月 去 北京？",
             "Wǒ jiǔ yuè qù Běijīng Dàxué dú shū.\nWèn: Tā jǐ yuè qù Běijīng?"),
            (["看 电视 [kàn diànshì]", "买 水果 [mǎi shuǐguǒ]", "写 汉字 [xiě Hànzì]"], "A",
             "晚上 我 和 爸爸 妈妈 在 家 看 电视。\n问：他们 晚上 做 什么？",
             "Wǎnshang wǒ hé bàba māma zài jiā kàn diànshì.\nWèn: Tāmen wǎnshang zuò shénme?"),
            (["50 块 [50 kuài]", "60 块 [60 kuài]", "80 块 [80 kuài]"], "C",
             "这个 小 椅子 八十 块 钱， 不 贵。\n问：这个 小 椅子 多少 钱？",
             "Zhège xiǎo yǐzi bāshí kuài qián, bú guì.\nWèn: Zhège xiǎo yǐzi duōshao qián?"),
            (["后面 [hòumiàn]", "前面 [qiánmiàn]", "里面 [lǐmiàn]"], "A",
             "那个 小 商店 就 在 学校 后面。\n问：小 商店 在 学校 哪儿？",
             "Nàge xiǎo shāngdiàn jiù zài xuéxiào hòumiàn.\nWèn: Xiǎo shāngdiàn zài xuéxiào nǎr?"),
        ],
        "R1": [
            (P0(8), "电话", "diànhuà", True),
            (P1(4), "开车", "kāi chē", False),
            (P2(11), "米饭", "mǐfàn", True),
            (P0(11), "杯子", "bēizi", False),
            (P1(20), "高兴", "gāoxìng", True),
        ],
        "R2_PICS": [P0(41), P1(6), P3(38), P0(38), P0(42), P1(28)],
        "R2": [
            ("B", "外面 下 雨 了， 我们 明天 再 去 吧。", "Wàimiàn xià yǔ le, wǒmen míngtiān zài qù ba."),
            ("C", "爸爸 买 回 家 很 多 红 苹果。", "Bàba mǎi huí jiā hěn duō hóng píngguǒ."),
            ("F", "你 看， 小 猫 在 椅子 上 呢。", "Nǐ kàn, xiǎo māo zài yǐzi shang ne."),
            ("D", "老师， 这个 问题 我 会！", "Lǎoshī, zhège wèntí wǒ huì!"),
            ("A", "李 医生 在 大 医院 工作 了 十 年 了。", "Lǐ yīshēng zài dà yīyuàn gōngzuò le shí nián le."),
        ],
        "R3_OPTS": [
            "星期五。 [Xīngqīwǔ.]",
            "很 好听。 [Hěn hǎotīng.]",
            "在 房间 里。 [Zài fángjiān li.]",
            "二十五 岁。 [Èrshíwǔ suì.]",
            "我 不 爱 吃。 [Wǒ bú ài chī.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            ("D", "王 老师 今年 多 大 了？", "Wáng lǎoshī jīnnián duō dà le?"),
            ("A", "你们 星期几 有 汉语 课？", "Nǐmen xīngqījǐ yǒu Hànyǔ kè?"),
            ("C", "女儿 在 哪儿 写 字 呢？", "Nǚ'ér zài nǎr xiě zì ne?"),
            ("E", "你 再 吃 一点儿 米饭 吧？", "Nǐ zài chī yìdiǎnr mǐfàn ba?"),
            ("B", "她 唱 的 歌 怎么样？", "Tā chàng de gē zěnmeyàng?"),
        ],
        "R4_OPTS": [
            "看见 [kànjiàn]", "能 [néng]", "先生 [xiānsheng]", "名字 [míngzi]", "少 [shǎo]", "水 [shuǐ]",
        ],
        "R4": [
            ("F", "天气 很 热， 你 多 喝 一点儿 （　） 吧。", "Tiānqì hěn rè, nǐ duō hē yìdiǎnr ( ) ba."),
            ("A", "我 刚才 在 饭店 门口 （　） 张 老师 了。", "Wǒ gāngcái zài fàndiàn ménkǒu ( ) Zhāng lǎoshī le."),
            ("B", "明天 上午 九 点 前 你 （　） 来 学校 吗？", "Míngtiān shàngwǔ jiǔ diǎn qián nǐ ( ) lái xuéxiào ma?"),
            ("E", "今天 来 上课 的 人 很 （　）。", "Jīntiān lái shàngkè de rén hěn ( )."),
            ("C", "女：你 好， 请问 刘 （　） 在 家 吗？\n男：在， 请 进。", "Nǚ: Nǐ hǎo, qǐngwèn Liú ( ) zài jiā ma?\nNán: Zài, qǐng jìn."),
        ],
    },

    # ==================== ĐỀ 8 (H1M08) ====================
    {
        "code": "H1M08",
        "ten": "HSK 1 – Đề 8",
        "L1": [
            (P0(37), True, "他 喜欢 吃 面条。", "Tā xǐhuan chī miàntiáo."),
            (P1(28), False, "椅子 下面 有 一 只 大 狗。", "Yǐzi xiàmiàn yǒu yì zhī dà gǒu."),
            (P3(39), True, "王 小姐 正在 打 电话 呢。", "Wáng xiǎojiě zhèngzài dǎ diànhuà ne."),
            (P2(23), True, "北京 的 冬天 很 冷。", "Běijīng de dōngtiān hěn lěng."),
            (P0(40), False, "姐姐 坐 飞机 去 上海。", "Jiějie zuò fēijī qù Shànghǎi."),
        ],
        "L2": [
            ([P0(7), P0(8), P0(28)], "C", "请 把 那 把 椅子 拿 过来。", "Qǐng bǎ nà bǎ yǐzi ná guòlai."),
            ([P1(14), P1(13), P0(4)], "A", "现在 是 八 点 十五 分。", "Xiànzài shì bā diǎn shíwǔ fēn."),
            ([P3(17), P0(14), P3(12)], "B", "她们 两 个 人 很 爱 唱歌。", "Tāmen liǎng ge rén hěn ài chànggē."),
            ([P1(43), P3(4), P3(40)], "A", "妈妈 和 姐姐 在 商店 看 衣服 呢。", "Māma hé jiějie zài shāngdiàn kàn yīfu ne."),
            ([P1(3), P1(16), P2(5)], "C", "再见， 我 去 学校 上课 了。", "Zàijiàn, wǒ qù xuéxiào shàngkè le."),
        ],
        "L3_PICS": [P0(29), P2(34), P0(27), P1(40), P3(16), P2(4)],
        "L3": [
            ("D", "男：这些 水果 真 漂亮！\n女：是 今天 上午 新 买 的， 来 吃 一 个。", "Nán: Zhèxiē shuǐguǒ zhēn piàoliang!\nNǚ: Shì jīntiān shàngwǔ xīn mǎi de, lái chī yí ge."),
            ("B", "女：小 妹妹 今年 几 岁 了？\n男：五 岁 了， 已经 会 读 汉字 了。", "Nǚ: Xiǎo mèimei jīnnián jǐ suì le?\nNán: Wǔ suì le, yǐjīng huì dú Hànzì le."),
            ("E", "男：张 小姐 今天 很 忙 吗？\n女：是， 她 在 电脑 前面 工作 一 上午 了。", "Nán: Zhāng xiǎojiě jīntiān hěn máng ma?\nNǚ: Shì, tā zài diànnǎo qiánmiàn gōngzuò yí shàngwǔ le."),
            ("A", "女：下雨 了， 我们 怎么 回 家？\n男：我们 坐 出租车 回去 吧。", "Nǚ: Xià yǔ le, wǒmen zěnme huí jiā?\nNán: Wǒmen zuò chūzūchē huíqu ba."),
            ("F", "男：陈 医生， 他 身体 怎么样？\n女：没 什么 大 问题， 多 休息。", "Nán: Chén yīshēng, tā shēntǐ zěnmeyàng?\nNǚ: Méi shénme dà wèntí, duō xiūxi."),
        ],
        "L4": [
            (["喝 茶 [hē chá]", "喝 咖啡 [hē kāfēi]", "喝 水 [hē shuǐ]"], "A",
             "爷爷 不 喝 冷 水， 他 每天 上午 都 喝 茶。\n问：爷爷 上午 喝 什么？",
             "Yéye bù hē lěng shuǐ, tā měi tiān shàngwǔ dōu hē chá.\nWèn: Yéye shàngwǔ hē shénme?"),
            (["3 本 [3 běn]", "4 本 [4 běn]", "7 本 [7 běn]"], "B",
             "我 今天 去 书店 买 了 四 本 汉语 书。\n问：他 买 了 几 本 书？",
             "Wǒ jīntiān qù shūdiàn mǎile sì běn Hànyǔ shū.\nWèn: Tā mǎile jǐ běn shū?"),
            (["学校 [xuéxiào]", "家 里 [jiā li]", "饭店 [fàndiàn]"], "B",
             "今天 星期日， 我 不 去 工作， 在 家 里 做 饭。\n问：他 今天 在 哪儿？",
             "Jīntiān xīngqīrì, wǒ bú qù gōngzuò, zài jiā li zuò fàn.\nWèn: Tā jīntiān zài nǎr?"),
            (["十 点 [shí diǎn]", "十一 点 [shíyī diǎn]", "十二 点 [shí'èr diǎn]"], "A",
             "晚上 十 点 了， 儿子， 去 睡觉 吧。\n问：现在 几 点 了？",
             "Wǎnshang shí diǎn le, érzi, qù shuìjiào ba.\nWèn: Xiànzài jǐ diǎn le?"),
            (["同学 [tóngxué]", "老师 [lǎoshī]", "医生 [yīshēng]"], "A",
             "这 位 是 李 明， 是 我 的 大学 同学。\n问：李 明 是 谁？",
             "Zhè wèi shì Lǐ Míng, shì wǒ de dàxué tóngxué.\nWèn: Lǐ Míng shì shéi?"),
        ],
        "R1": [
            (P1(35), "茶", "chá", True),
            (P0(31), "电视", "diànshì", False),
            (P1(33), "写字", "xiě zì", True),
            (P3(23), "小猫", "xiǎomāo", False),
            (P3(36), "九点", "jiǔ diǎn", True),
        ],
        "R2_PICS": [P2(39), P3(20), P1(30), P3(12), P0(42), P2(19)],
        "R2": [
            ("F", "桌子 上 的 苹果 很 好吃。", "Zhuōzi shang de píngguǒ hěn hǎochī."),
            ("A", "这个 汉语 题 不 太 好 做。", "Zhège Hànyǔ tí bú tài hǎo zuò."),
            ("D", "今天 中午 我 在 家 做 饭。", "Jīntiān zhōngwǔ wǒ zài jiā zuò fàn."),
            ("C", "再见， 下 个 星期六 见！", "Zàijiàn, xià ge xīngqīliù jiàn!"),
            ("B", "她 开 车 三 年 多 了。", "Tā kāi chē sān nián duō le."),
        ],
        "R3_OPTS": [
            "六 十 块。 [Liùshí kuài.]",
            "在 学校 后面。 [Zài xuéxiào hòumiàn.]",
            "我 妈妈。 [Wǒ māma.]",
            "明天 上午。 [Míngtiān shàngwǔ.]",
            "不 冷。 [Bù lěng.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            ("C", "这 件 漂亮 的 衣服 是 谁 买 的？", "Zhè jiàn piàoliang de yīfu shì shéi mǎi de?"),
            ("A", "请问， 这 本 书 多少 钱？", "Qǐngwèn, zhè běn shū duōshao qián?"),
            ("D", "你们 什么 时候 去 火车站？", "Nǐmen shénme shíhou qù huǒchēzhàn?"),
            ("B", "那个 中国 饭馆儿 在 哪儿？", "Nàge Zhōngguó fànguǎnr zài nǎr?"),
            ("E", "今天 外面 天气 冷 吗？", "Jīntiān wàimiàn tiānqì lěng ma?"),
        ],
        "R4_OPTS": [
            "岁 [suì]", "说话 [shuōhuà]", "医院 [yīyuàn]", "名字 [míngzi]", "高兴 [gāoxìng]", "坐 [zuò]",
        ],
        "R4": [
            ("A", "李 老师 的 儿子 今年 七 （　） 了。", "Lǐ lǎoshī de érzi jīnnián qī ( ) le."),
            ("C", "他 身体 不 好， 上午 去 （　） 看 医生 了。", "Tā shēntǐ bù hǎo, shàngwǔ qù ( ) kàn yīshēng le."),
            ("E", "能 来 中国 学习， 我 很 （　）。", "Néng lái Zhōngguó xuéxí, wǒ hěn ( )."),
            ("B", "上课 了， 请 大 家 不 要 （　）。", "Shàngkè le, qǐng dàjiā bú yào ( )."),
            ("F", "男：我们 怎么 去 机场？\n女：太 晚 了， （　） 出租车 去 吧。", "Nán: Wǒmen zěnme qù jīchǎng?\nNǚ: Tài wǎn le, ( ) chūzūchē qù ba."),
        ],
    },

    # ==================== ĐỀ 9 (H1M09) ====================
    {
        "code": "H1M09",
        "ten": "HSK 1 – Đề 9",
        "L1": [
            (P1(2), True, "王 先生 在 打 电话。", "Wáng xiānsheng zài dǎ diànhuà."),
            (P2(36), False, "她 在 商店 买 水果。", "Tā zài shāngdiàn mǎi shuǐguǒ."),
            (P0(7), True, "桌子 上 有 五 本 书。", "Zhuōzi shang yǒu wǔ běn shū."),
            (P3(40), True, "妈妈 和 女儿 在 看 电影。", "Māma hé nǚ'ér zài kàn diànyǐng."),
            (P1(37), False, "这 是 我 姐姐 的 小 猫。", "Zhè shì wǒ jiějie de xiǎo māo."),
        ],
        "L2": [
            ([P1(15), P1(13), P3(36)], "A", "我 早上 七 点 十 分 去 上学。", "Wǒ zǎoshang qī diǎn shí fēn qù shàngxué."),
            ([P2(33), P0(5), P2(11)], "A", "早上 我 想 喝 一 杯 牛奶。", "Zǎoshang wǒ xiǎng hē yì bēi niúnǎi."),
            ([P0(21), P3(19), P1(4)], "C", "他 每天 骑 自行车 去 学校。", "Tā měi tiān qí zìxíngchē qù xuéxiào."),
            ([P3(13), P0(31), P0(8)], "A", "爸爸 想 买 一 个 大 电视。", "Bàba xiǎng mǎi yí ge dà diànshì."),
            ([P1(18), P1(16), P1(3)], "B", "他们 两 个 先生 是 好 朋友。", "Tāmen liǎng ge xiānsheng shì hǎo péngyou."),
        ],
        "L3_PICS": [P2(24), P3(25), P0(27), P1(6), P2(43), P0(40)],
        "L3": [
            ("B", "男：你 在 写 什么 呢？\n女：我 在 写 今天 学 的 汉字。", "Nán: Nǐ zài xiě shénme ne?\nNǚ: Wǒ zài xiě jīntiān xué de Hànzì."),
            ("D", "女：今天 怎么 下 雨 了？\n男：是 啊， 天气 有点儿 冷。", "Nǚ: Jīntiān zěnme xià yǔ le?\nNán: Shì a, tiānqì yǒudiǎnr lěng."),
            ("F", "男：明天 几 点 的 火车？\n女：上午 八 点 二十 分。", "Nán: Míngtiān jǐ diǎn de huǒchē?\nNǚ: Shàngwǔ bā diǎn èrshí fēn."),
            ("E", "女：女儿 今天 吃 了 不少 菜。\n男：对， 她 很 喜欢 你 做 的 菜。", "Nǚ: Nǚ'ér jīntiān chīle bù shǎo cài.\nNán: Duì, tā hěn xǐhuan nǐ zuò de cài."),
            ("A", "女：来， 我们 两 个 在 这儿 照 张 相 吧。\n男：好 啊！", "Nǚ: Lái, wǒmen liǎng ge zài zhèr zhào zhāng xiàng ba.\nNán: Hǎo a!"),
        ],
        "L4": [
            (["北京 [Běijīng]", "上海 [Shànghǎi]", "医院 [yīyuàn]"], "A",
             "我 姐姐 在 北京 工作 三 年 了。\n问：姐姐 在 哪儿 工作？",
             "Wǒ jiějie zài Běijīng gōngzuò sān nián le.\nWèn: Jiějie zài nǎr gōngzuò?"),
            (["茶 [chá]", "苹果 [píngguǒ]", "衣服 [yīfu]"], "C",
             "妈妈 昨天 去 商店 给 我 买 了 两 件 新 衣服。\n问：妈妈 买 了 什么？",
             "Māma zuótiān qù shāngdiàn gěi wǒ mǎile liǎng jiàn xīn yīfu.\nWèn: Māma mǎile shénme?"),
            (["星期一 [xīngqīyī]", "星期三 [xīngqīsān]", "星期六 [xīngqīliù]"], "C",
             "今天 星期五， 明天 我 不 去 学校， 在 家 看 书。\n问：明天 是 星期几？",
             "Jīntiān xīngqīwǔ, míngtiān wǒ bú qù xuéxiào, zài jiā kàn shū.\nWèn: Míngtiān shì xīngqījǐ?"),
            (["15", "25", "35"], "B",
             "我们 班 有 二十五 个 学生。\n问：他们 班 有 多少 个 学生？",
             "Wǒmen bān yǒu èrshíwǔ ge xuésheng.\nWèn: Tāmen bān yǒu duōshao ge xuésheng?"),
            (["不 会 做 饭 [bú huì zuò fàn]", "很 会 做 饭 [hěn huì zuò fàn]", "不 爱 吃 米饭 [bú ài chī mǐfàn]"], "B",
             "我 爸爸 做 的 中国 菜 非常 好吃。\n问：爸爸 怎么样？",
             "Wǒ bàba zuò de Zhōngguó cài fēicháng hǎochī.\nWèn: Bàba zěnmeyàng?"),
        ],
        "R1": [
            (P0(28), "椅子", "yǐzi", True),
            (P2(6), "米饭", "mǐfàn", False),
            (P1(34), "听", "tīng", True),
            (P3(18), "老师", "lǎoshī", False),
            (P0(31), "电脑", "diànnǎo", True),
        ],
        "R2_PICS": [P3(4), P1(26), P0(26), P1(10), P0(42), P2(28)],
        "R2": [
            ("A", "晚上 爸爸 和 儿子 一起 读 书。", "Wǎnshang bàba hé érzi yìqǐ dú shū."),
            ("D", "外面 太 冷 了， 多 穿 一点儿 衣服。", "Wàimiàn tài lěng le, duō chuān yìdiǎnr yīfu."),
            ("F", "他们 家 的 大 狗 很 好， 我 很 喜欢。", "Tāmen jiā de dà gǒu hěn hǎo, wǒ hěn xǐhuan."),
            ("C", "星期日 她 去 商店 买 了 很 多 东西。", "Xīngqīrì tā qù shāngdiàn mǎile hěn duō dōngxi."),
            ("B", "对不起， 我 今天 没 带 钱。", "Duìbuqǐ, wǒ jīntiān méi dài qián."),
        ],
        "R3_OPTS": [
            "会 说 一点儿。 [Huì shuō yìdiǎnr.]",
            "九 月 十 号。 [Jiǔ yuè shí hào.]",
            "在 椅子 下面。 [Zài yǐzi xiàmiàn.]",
            "王 医生。 [Wáng yīshēng.]",
            "去 买 水果 了。 [Qù mǎi shuǐguǒ le.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            ("E", "妈妈 去 哪儿 了？", "Māma qù nǎr le?"),
            ("A", "你 弟弟 会 说 汉语 吗？", "Nǐ dìdi huì shuō Hànyǔ ma?"),
            ("C", "你 看见 我 的 小 猫 了 吗？", "Nǐ kànjiàn wǒ de xiǎo māo le ma?"),
            ("D", "医院 里 那个 人 是 谁？", "Yīyuàn li nàge rén shì shéi?"),
            ("B", "请问， 哪 天 是 老师 的 生日？", "Qǐngwèn, nǎ tiān shì lǎoshī de shēngrì?"),
        ],
        "R4_OPTS": [
            "前面 [qiánmiàn]", "昨天 [zuótiān]", "谢谢 [xièxie]", "名字 [míngzi]", "本 [běn]", "吃饭 [chī fàn]",
        ],
        "R4": [
            ("E", "桌子 上 有 三 （　） 汉语 书。", "Zhuōzi shang yǒu sān ( ) Hànyǔ shū."),
            ("A", "请 看， 我 家 就 在 那个 学校 （　）。", "Qǐng kàn, wǒ jiā jiù zài nàge xuéxiào ( )."),
            ("B", "（　） 下 雨 了， 我 没 去 看 电影。", "( ) xià yǔ le, wǒ méi qù kàn diànyǐng."),
            ("F", "中午 十二 点 了， 我们 一起 去 （　） 吧。", "Zhōngwǔ shí'èr diǎn le, wǒmen yìqǐ qù ( ) ba."),
            ("C", "女：（　） 你 送 我 回 家。\n男：不 客气， 明天 见。", "Nǚ: ( ) nǐ sòng wǒ huí jiā.\nNán: Bú kèqi, míngtiān jiàn."),
        ],
    },

    # ==================== ĐỀ 10 (H1M10) ====================
    {
        "code": "H1M10",
        "ten": "HSK 1 – Đề 10",
        "L1": [
            (P3(38), True, "这儿 有 很 多 苹果。", "Zhèr yǒu hěn duō píngguǒ."),
            (P0(17), True, "她 在 学校 工作， 是 老师。", "Tā zài xuéxiào gōngzuò, shì lǎoshī."),
            (P3(20), False, "他 每天 坐 火车 去 上班。", "Tā měi tiān zuò huǒchē qù shàngbān."),
            (P2(37), True, "那里 有 一 把 椅子。", "Nàlǐ yǒu yì bǎ yǐzi."),
            (P1(5), False, "弟弟 正在 写 汉字 呢。", "Dìdi zhèngzài xiě Hànzì ne."),
        ],
        "L2": [
            ([P0(32), P0(40), P0(29)], "C", "太 晚 了， 我们 坐 出租车 回 家 吧。", "Tài wǎn le, wǒmen zuò chūzūchē huí jiā ba."),
            ([P3(3), P0(9), P0(7)], "A", "妈妈 今天 买 了 三 个 新 杯子。", "Māma jīntiān mǎile sān ge xīn bēizi."),
            ([P2(36), P1(2), P2(17)], "C", "爸爸 很 爱 在 家 做 饭。", "Bàba hěn ài zài jiā zuò fàn."),
            ([P1(28), P1(37), P0(12)], "B", "这 只 大 狗 是 我 朋友 家 的。", "Zhè zhī dà gǒu shì wǒ péngyou jiā de."),
            ([P1(13), P0(4), P3(36)], "A", "现在 十 点 十 分， 休息 一下 吧。", "Xiànzài shí diǎn shí fēn, xiūxi yíxià ba."),
        ],
        "L3_PICS": [P0(15), P3(41), P0(27), P2(29), P3(37), P1(43)],
        "L3": [
            ("B", "女：你好， 王 先生 在 办公室 吗？\n男：在， 您 请 坐。", "Nǚ: Nǐ hǎo, Wáng xiānsheng zài bàngōngshì ma?\nNán: Zài, nín qǐng zuò."),
            ("F", "男：这 两 件 衣服 你 喜欢 哪 件？\n女：白色 的 这 件 很 漂亮。", "Nán: Zhè liǎng jiàn yīfu nǐ xǐhuan nǎ jiàn?\nNǚ: Báisè de zhè jiàn hěn piàoliang."),
            ("E", "男：小 儿子 睡觉 了 吗？\n女：睡 了， 九 点 就 睡 了。", "Nán: Xiǎo érzi shuìjiào le ma?\nNǚ: Shuì le, jiǔ diǎn jiù shuì le."),
            ("A", "女：他们 在 做 什么 呢？\n男：他们 在 看 电脑 上 的 东西。", "Nǚ: Tāmen zài zuò shénme ne?\nNán: Tāmen zài kàn diànnǎo shang de dōngxi."),
            ("D", "男：你 去 商店 买 什么 了？\n女：买 了 不少 水果。", "Nán: Nǐ qù shāngdiàn mǎi shénme le?\nNǚ: Mǎile bù shǎo shuǐguǒ."),
        ],
        "L4": [
            (["茶 [chá]", "水 [shuǐ]", "牛奶 [niúnǎi]"], "C",
             "女儿 每天 早上 都 喝 一 杯 热 牛奶。\n问：女儿 早上 喝 什么？",
             "Nǚ'ér měi tiān zǎoshang dōu hē yì bēi rè niúnǎi.\nWèn: Nǚ'ér zǎoshang hē shénme?"),
            (["4 岁 [4 suì]", "14 岁 [14 suì]", "40 岁 [40 suì]"], "B",
             "我 弟弟 今年 十四 岁， 是 中学生。\n问：弟弟 今年 多 大 了？",
             "Wǒ dìdi jīnnián shísì suì, shì zhōngxuéshēng.\nWèn: Dìdi jīnnián duō dà le?"),
            (["医院 [yīyuàn]", "书店 [shūdiàn]", "火车站 [huǒchēzhàn]"], "B",
             "下午 我 想 去 学校 后面 的 书店 买 几 本 书。\n问：她 下午 想 去 哪儿？",
             "Xiàwǔ wǒ xiǎng qù xuéxiào hòumiàn de shūdiàn mǎi jǐ běn shū.\nWèn: Tā xiàwǔ xiǎng qù nǎr?"),
            (["星期二 [xīngqī'èr]", "星期三 [xīngqīsān]", "星期四 [xīngqīsì]"], "A",
             "明天 星期三， 我们 有 两 节 汉语 课。\n问：今天 星期几？",
             "Míngtiān xīngqīsān, wǒmen yǒu liǎng jié Hànyǔ kè.\nWèn: Jīntiān xīngqījǐ?"),
            (["38 块 [38 kuài]", "48 块 [48 kuài]", "80 块 [80 kuài]"], "A",
             "这个 大 西瓜 三十八 块 钱。\n问：这个 西瓜 多少 钱？",
             "Zhège dà xīguā sānshíbā kuài qián.\nWèn: Zhège xīguā duōshao qián?"),
        ],
        "R1": [
            (P2(3), "喝水", "hē shuǐ", True),
            (P0(7), "电脑", "diànnǎo", False),
            (P3(12), "做饭", "zuò fàn", True),
            (P1(13), "八点", "bā diǎn", False),
            (P3(30), "再见", "zàijiàn", True),
        ],
        "R2_PICS": [P1(24), P3(25), P0(41), P1(39), P0(42), P2(11)],
        "R2": [
            ("F", "中午 我 吃 了 一 大 碗 米饭。", "Zhōngwǔ wǒ chīle yí dà wǎn mǐfàn."),
            ("C", "姐姐 的 朋友 在 医院 做 医生。", "Jiějie de péngyou zài yīyuàn zuò yīshēng."),
            ("A", "下 个 月 我 想 去 中国 看 长城。", "Xià ge yuè wǒ xiǎng qù Zhōngguó kàn Chángchéng."),
            ("D", "她 正在 家 里 给 同学 打 电话 呢。", "Tā zhèngzài jiā li gěi tóngxué dǎ diànhuà ne."),
            ("B", "妈妈 教 我 写 中国 字。", "Māma jiāo wǒ xiě Zhōngguó zì."),
        ],
        "R3_OPTS": [
            "很 好吃。 [Hěn hǎochī.]",
            "我 的 汉语 老师。 [Wǒ de Hànyǔ lǎoshī.]",
            "下午 四 点。 [Xiàwǔ sì diǎn.]",
            "在 飞机 上。 [Zài fēijī shang.]",
            "没 买 什么。 [Méi mǎi shénme.]",
            "好 的， 谢谢！ [Hǎo de, xièxie!]",
        ],
        "R3": [
            ("A", "这个 饭馆儿 的 菜 怎么样？", "Zhège fànguǎnr de cài zěnmeyàng?"),
            ("B", "前面 说话 的 那个 人 是 谁？", "Qiánmiàn shuōhuà de nàge rén shì shéi?"),
            ("E", "你 上午 去 商店 买 什么 了？", "Nǐ shàngwǔ qù shāngdiàn mǎi shénme le?"),
            ("C", "爸爸 几 点 回 家？", "Bàba jǐ diǎn huí jiā?"),
            ("D", "张 先生 现在 在 哪儿 呢？", "Zhāng xiānsheng xiànzài zài nǎr ne?"),
        ],
        "R4_OPTS": [
            "看 [kàn]", "月 [yuè]", "不客气 [bú kèqi]", "名字 [míngzi]", "多 [duō]", "汉语 [Hànyǔ]",
        ],
        "R4": [
            ("F", "大卫 学习 （　） 一 年 了， 说 得 很 好。", "Dàwèi xuéxí ( ) yì nián le, shuō de hěn hǎo."),
            ("B", "一 年 有 十二 个 （　）。", "Yì nián yǒu shí'èr ge ( )."),
            ("E", "今天 商店 里 的 人 真 （　）！", "Jīntiān shāngdiàn li de rén zhēn ( )!"),
            ("A", "星期六 晚上 我们 一起 去 （　） 电影， 好 吗？", "Xīngqīliù wǎnshang wǒmen yìqǐ qù ( ) diànyǐng, hǎo ma?"),
            ("C", "男：谢谢 你 帮 我 买 火车票。\n女：（　）。", "Nán: Xièxie nǐ bāng wǒ mǎi huǒchēpiào.\nNǚ: ( )."),
        ],
    },
]


def main() -> int:
    specs = [make_hsk1_exam(cfg) for cfg in HSK1_CONFIGS]
    save_and_seed_exams(specs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
