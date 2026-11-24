"""Tạo tệp dữ liệu chuẩn JSON và nạp Đề 3 gốc Hanban cho HSK 2 (H21003), HSK 3 (H31003) và HSK 4 (H41003).

Nguồn: 国家汉办/孔子学院总部 – 新汉语水平考试 HSK 2.0 (H21003, H31003, H41003) từ bộ PDF + MP3 gốc.
- Lưu 3 tệp JSON chuẩn vào backend/scripts/data/{hsk2_h21003,hsk3_h31003,hsk4_h41003}.json
- Kiểm tra toàn bộ tệp hình + âm thanh + quy tắc câu hỏi trước khi ghi CSDL
- An toàn khi chạy lại nhiều lần (idempotent theo ma_de).
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from scripts.seed_hsk234_de2 import DATA_DIR, import_exam_data, opts_img, opts_text, tf


# ==============================================================================
# 1. HSK 2 – Đề 3 (H21003) — 60 câu tính điểm + 9 câu ví dụ
# ==============================================================================
def build_h21003() -> dict:
    slug = "hsk2_h21003"
    img = lambda n: f"exams/{slug}/img/{n:03d}.jpg"
    plan = []

    # Part 1: Nghe 1–10 (Đúng/Sai với hình)
    l1 = [
        (True, 0, True, "我们家有三个人。"),
        (True, 1, False, "我每天坐公共汽车去上班。"),
        (False, 2, True, "今天是二十三号。"),
        (False, 3, False, "她每天都去游泳。"),
        (False, 4, True, "您说得太好了！"),
        (False, 5, True, "你生病了，要多喝水，多休息。"),
        (False, 6, True, "长时间看电脑，对眼睛不好。"),
        (False, 7, False, "中午朋友送了我两张电影票。"),
        (False, 8, False, "到了前面再向右走。"),
        (False, 9, True, "妻子喜欢吃早饭时看报纸。"),
        (False, 10, False, "他这次没考好，所以不高兴。"),
        (False, 11, False, "这鱼十块钱一斤，不错吧？"),
    ]
    for ex, pic, ok, said in l1:
        plan.append({
            "part": 1, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "tep_hinh": img(pic), "loi_nghe": said, "phuong_an": tf(ok)},
        })

    # Part 2: Nghe 11–15 (6 hình A–F: 12..17) & 16–20 (5 hình A–E: 18..22)
    plan.append({
        "part": 2,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [12, 13, 14, 15, 16, 17])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：你喜欢什么运动？\n女：我最喜欢踢足球。", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：你也想吃？来，给你。\n男：你和狗说话，它能听懂吗？", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：等等我，你走得太快了！\n女：你太慢了。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：还冷吗？\n女：现在不冷了，谢谢妈妈。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：这些衣服你什么时候洗的？我怎么没看见。\n女：就是昨天下午。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：你好！我的车出问题了，你们能来帮我看一下吗？\n男：好的，请告诉我您在哪儿。", "dap_an_thu_tu": 3}, False],
        ],
    })
    plan.append({
        "part": 2,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [18, 19, 20, 21, 22])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：你在想什么呢？\n女：我？我在想下个月去哪儿旅游好呢。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：喂，你到北京了吗？\n男：到了，我现在已经到饭店了，正想休息休息呢。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：在哪儿呢？我怎么找不到？\n女：你看，就在那儿！", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：先生您好，您想喝点儿什么？\n男：我要一杯咖啡，谢谢！", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：您女儿怎么星期六还去学校？\n女：她正在学习跳舞，每星期上一次课。", "dap_an_thu_tu": 2}, False],
        ],
    })

    # Part 3: Nghe 21–30
    l3 = [
        (True, "A", ["红色 [hóngsè]", "黑色 [hēisè]", "白色 [báisè]"],
         "男：小王，这里有几个杯子，哪个是你的？\n女：左边那个红色的是我的。\n问：小王的杯子是什么颜色的？"),
        (False, "B", ["学习 [xuéxí]", "运动 [yùndòng]", "跳舞 [tiàowǔ]"],
         "女：外面天气很好，我们出去运动运动？\n男：好，打篮球怎么样？\n问：男的想做什么？"),
        (False, "A", ["很 贵 [hěn guì]", "很 便宜 [hěn piányi]", "不 好 找 [bù hǎo zhǎo]"],
         "男：你在这个商店买过东西吗？\n女：买过一次。这儿的东西还不错，就是太贵了。\n问：这个商店的东西怎么样？"),
        (False, "B", ["8 点 30 分 [8 diǎn 30 fēn]", "8 点 40 分 [8 diǎn 40 fēn]", "8 点 50 分 [8 diǎn 50 fēn]"],
         "女：小李怎么还没来，都八点四十了。\n男：我已经给他打电话了，他说在出租车上，几分钟后就到。\n问：现在几点了？"),
        (False, "B", ["教室 [jiàoshì]", "商店 [shāngdiàn]", "医院 [yīyuàn]"],
         "男：小姐，这件衣服有大一点儿的吗？\n女：真对不起，这是最后一件了。\n问：说话人最可能在哪儿？"),
        (False, "C", ["他 妹妹 [tā mèimei]", "他 弟弟 [tā dìdi]", "他 儿子 [tā érzi]"],
         "女：你今天买的东西真不少。\n男：明天是我儿子的生日，都是给他买的。\n问：明天是谁的生日？"),
        (False, "A", ["菜 [cài]", "米饭 [mǐfàn]", "水果 [shuǐguǒ]"],
         "男：服务员，我们想再要一个菜。\n女：好的，您要什么菜？\n问：男的向服务员要什么？"),
        (False, "C", ["想 唱歌 [xiǎng chànggē]", "想 看 电视 [xiǎng kàn diànshì]", "想 看 电影 [xiǎng kàn diànyǐng]"],
         "女：你给我打电话了？对不起，什么事？\n男：我想问你晚上去不去看电影？\n问：男的为什么给女的打电话？"),
        (False, "A", ["手机 [shǒujī]", "手表 [shǒubiǎo]", "自行车 [zìxíngchē]"],
         "男：你看见我的手机了吗？\n女：让我想想，你看是不是在床上？\n问：男的在找什么？"),
        (False, "B", ["姐姐 [jiějie]", "朋友 [péngyou]", "同学 [tóngxué]"],
         "女：你的车是什么时候买的？\n男：不是买的，去年我的一个朋友出国了，车就送给我了。\n问：车是谁送的？"),
        (False, "C", ["不 想 回 家 [bù xiǎng huí jiā]", "不 认识 路 [bú rènshi lù]", "住 得 不 远 [zhù de bù yuǎn]"],
         "男：今天太晚了，我送你回家吧。\n女：没关系，我家离这儿很近。\n问：女的是什么意思？"),
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
        (False, "C", ["不 会 说 [bú huì shuō]", "不 太 好 [bú tài hǎo]", "非常 好 [fēicháng hǎo]"],
         "男：你们学校有两个外国学生？\n女：是，你怎么知道的？\n男：听我哥说的。他们会说汉语吗？\n女：他们的汉语都非常好，大家很喜欢他们。\n问：那两个外国学生的汉语怎么样？"),
        (False, "A", ["送 她 [sòng tā]", "去 北京 [qù Běijīng]", "叫 她 起床 [jiào tā qǐchuáng]"],
         "女：我明天去北京，上午的飞机，你能送我去机场吗？\n男：没问题，明天我休息。几点的飞机？\n女：上午九点二十的。谢谢你！\n男：不客气！再见。\n问：女的想请男的做什么？"),
        (False, "B", ["多 买 些 [duō mǎi xiē]", "少 买 些 [shǎo mǎi xiē]", "别 卖 了 [bié mài le]"],
         "男：苹果很便宜，我们买一些吧？\n女：买，多吃水果对身体好。\n男：那多买几斤？\n女：别买太多，买几斤就可以了。\n问：女的是什么意思？"),
        (False, "C", ["生病 了 [shēngbìng le]", "回答 错 了 [huídá cuò le]", "打 错 电话 了 [dǎ cuò diànhuà le]"],
         "女：你好，请问张小姐在吗？\n男：你找谁？\n女：张欢，张小姐是在这儿工作吗？\n男：你打错了，我们这儿没有叫张欢的。\n问：女的怎么了？"),
        (False, "A", ["同学 [tóngxué]", "老师 [lǎoshī]", "医生 [yīshēng]"],
         "男：今天星期几？\n女：星期日。\n男：我的天！今天下午我同学要来。现在几点了？\n女：快两点了。\n问：今天下午谁要来？"),
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
            [{"dang": "chon_bo_chung", "noi_dung": "雨 不 下 了， 天 晴 了。", "pinyin": "Yǔ bú xià le, tiān qíng le.", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "他 给 女 朋友 买了 一 个 新 手机。", "pinyin": "Tā gěi nǚ péngyou mǎile yí ge xīn shǒujī.", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "准备 好 了 吗？ 好， 笑一笑。", "pinyin": "Zhǔnbèi hǎo le ma? Hǎo, xiàoyixiào.", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "非常 欢迎 你 来 我们 公司 工作！", "pinyin": "Fēicháng huānyíng nǐ lái wǒmen gōngsī gōngzuò!", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "每 天 早上 她 都 要 慢 跑 一 小时。", "pinyin": "Měi tiān zǎoshang tā dōu yào màn pǎo yì xiǎoshí.", "dap_an_thu_tu": 1}, False],
        ],
    })

    # Part 6: Đọc 41–45 (Điền từ A–F)
    plan.append({
        "part": 6,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text(["一起 [yìqǐ]", "西瓜 [xīguā]", "题 [tí]", "号 [hào]", "贵 [guì]", "雪 [xuě]"]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "这儿 的 羊肉 很 好吃， 但是 也 很 （　）。", "pinyin": "Zhèr de yángròu hěn hǎochī, dànshì yě hěn ( ).", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "天 阴 了， 可能 要 下 （　）。", "pinyin": "Tiān yīn le, kěnéng yào xià ( ).", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 要 睡觉 了， 那些 （　） 明天 再 做 吧。", "pinyin": "Wǒ yào shuìjiào le, nàxiē ( ) míngtiān zài zuò ba.", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 希望 能 和 你 在 （　）。", "pinyin": "Wǒ xīwàng néng hé nǐ zài ( ).", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 今年 14 岁， 我 的 生日 是 6 月 7 （　）。", "pinyin": "Wǒ jīnnián 14 suì, wǒ de shēngrì shì 6 yuè 7 ( ).", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "男： 现在 （　） 多少 钱 一 斤？\n女： 我 看看， 这儿 写着 呢， 5 元 一 斤。", "pinyin": "Nán: Xiànzài ( ) duōshao qián yì jīn?\nNǚ: Wǒ kànkan, zhèr xiězhe ne, 5 yuán yì jīn.", "dap_an_thu_tu": 2}, False],
        ],
    })

    # Part 7: Đọc 46–50 (Đúng/Sai ★)
    r3 = [
        (True, True,
         "现在 是 11 点 30 分， 他们 已经 游了 20 分钟 了。\n★ 他们 11 点 10 分 开始 游泳。",
         "Xiànzài shì 11 diǎn 30 fēn, tāmen yǐjīng yóule 20 fēnzhōng le.\n★ Tāmen 11 diǎn 10 fēn kāishǐ yóuyǒng."),
        (True, False,
         "我 会 跳舞， 但 跳 得 不 怎么样。\n★ 我 跳 得 非常 好。",
         "Wǒ huì tiàowǔ, dàn tiào de bù zěnmeyàng.\n★ Wǒ tiào de fēicháng hǎo."),
        (False, True,
         "您 请 进， 这 就 是 我 的 家。 这个 房间 是 我 和 我 丈夫 的， 旁边 那个 小 的 是 孩子 的 房间。\n★ 我们 的 房间 比 孩子 的 大。",
         "Nín qǐng jìn, zhè jiù shì wǒ de jiā. Zhège fángjiān shì wǒ hé wǒ zhàngfu de, pángbiān nàge xiǎo de shì háizi de fángjiān.\n★ Wǒmen de fángjiān bǐ háizi de dà."),
        (False, False,
         "我 爸爸 不 爱 喝 咖啡， 他 喜欢 喝 茶， 每 天 上午 都 会 喝 几 杯 热 茶。\n★ 爸爸 觉得 茶 不 好喝。",
         "Wǒ bàba bú ài hē kāfēi, tā xǐhuan hē chá, měi tiān shàngwǔ dōu huì hē jǐ bēi rè chá.\n★ Bàba juéde chá bù hǎohē."),
        (False, True,
         "他 在 火车站 工作， 每 天 都 很 忙， 但 他 很 少 说 累， 他 觉得 能 帮助 人们 是 他 最大 的 快乐。\n★ 他 很 喜欢 他 的 工作。",
         "Tā zài huǒchēzhàn gōngzuò, měi tiān dōu hěn máng, dàn tā hěn shǎo shuō lèi, tā juéde néng bāngzhù rénmen shì tā zuìdà de kuàilè.\n★ Tā hěn xǐhuan tā de gōngzuò."),
        (False, False,
         "这些 桌子 和 椅子 都 是 100 多 年 前 做 的， 所以 比 现在 的 要 贵 很 多。\n★ 这些 桌子、 椅子 都 很 新。",
         "Zhèxiē zhuōzi hé yǐzi dōu shì 100 duō nián qián zuò de, suǒyǐ bǐ xiànzài de yào guì hěn duō.\n★ Zhèxiē zhuōzi, yǐzi dōu hěn xīn."),
        (False, False,
         "他 做 的 菜 比 我 做 的 好吃， 但是 因为 工作 忙， 他 很 少 做。\n★ 他 不 会 做 菜。",
         "Tā zuò de cài bǐ wǒ zuò de hǎochī, dànshì yīnwèi gōngzuò máng, tā hěn shǎo zuò.\n★ Tā bú huì zuò cài."),
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
                "对不起， 再 给 我 一 天 时间？ [Duìbuqǐ, zài gěi wǒ yì tiān shíjiān?]",
                "王 老师， 你 的 电话。 [Wáng lǎoshī, nǐ de diànhuà.]",
                "一 个 鸡蛋， 喝了 些 牛奶。 [Yí ge jīdàn, hēle xiē niúnǎi.]",
                "你 出去 的 时候 多 穿 些 衣服。 [Nǐ chūqù de shíhou duō chuān xiē yīfu.]",
                "他 在 哪儿 呢？ 你 看见 他 了 吗？ [Tā zài nǎr ne? Nǐ kànjiàn tā le ma?]",
                "这 船 是 从 上海 开 来 的。 [Zhè chuán shì cóng Shànghǎi kāi lái de.]",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "他 还 在 教室 里 学习。", "pinyin": "Tā hái zài jiàoshì li xuéxí.", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "它 很 大， 能 坐 一千 多 人。", "pinyin": "Tā hěn dà, néng zuò yìqiān duō rén.", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "今天 真 冷， 有 零 下 10℃ 吧？", "pinyin": "Jīntiān zhēn lěng, yǒu líng xià 10℃ ba?", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "第一 次 来 这儿？ 早上 吃 什么 了？", "pinyin": "Dì-yī cì lái zhèr? Zǎoshang chī shénme le?", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "那 本 书 你 读 完 了 吗？", "pinyin": "Nà běn shū nǐ dú wán le ma?", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "谢谢！ 是 谁？", "pinyin": "Xièxie! Shì shéi?", "dap_an_thu_tu": 2}, False],
        ],
    })
    plan.append({
        "part": 8,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text([
                "这个 名字 很 有 意思。 [Zhège míngzi hěn yǒu yìsi.]",
                "太 多 了 吧？ 这 是 药！ [Tài duō le ba? Zhè shì yào!]",
                "你 姐姐 真 高， 这么 漂亮， 她 有 男 朋友 了 吗？ [Nǐ jiějie zhēn gāo, zhème piàoliang, tā yǒu nán péngyou le ma?]",
                "在 门 后面 玩儿 呢。 [Zài mén hòumiàn wánr ne.]",
                "您 看 了 吗？ 没 什么 问题 吧？ [Nín kàn le ma? Méi shénme wèntí ba?]",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "这个 字 你 写 错 了， 是 “白”， 不 是 “百”。", "pinyin": "Zhège zì nǐ xiě cuò le, shì “bái”, bú shì “bǎi”.", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "你 要 给 她 介绍 一 个 吗？", "pinyin": "Nǐ yào gěi tā jièshào yí ge ma?", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 的 小猫 呢？", "pinyin": "Wǒ de xiǎomāo ne?", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "我 爸爸 姓 刘， 我 妈妈 姓 杨， 所以 我 叫 刘杨。", "pinyin": "Wǒ bàba xìng Liú, wǒ māma xìng Yáng, suǒyǐ wǒ jiào Liúyáng.", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "医生 说 大人 一 天 可以 吃 4 次。", "pinyin": "Yīshēng shuō dàren yì tiān kěyǐ chī 4 cì.", "dap_an_thu_tu": 2}, False],
        ],
    })

    return {
        "exam": {
            "code": "H21003",
            "level": "HSK2",
            "ten": "HSK 2 – Đề 3",
            "phut": 55,
            "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（二级）H21003",
            "audio": f"exams/{slug}/listening.mp3",
            "img_dir": f"exams/{slug}/img",
        },
        "plan": plan,
    }


# ==============================================================================
# 2. HSK 3 – Đề 3 (H31003) — 80 câu tính điểm + 10 câu ví dụ
# ==============================================================================
def build_h31003() -> dict:
    slug = "hsk3_h31003"
    plan = []

    # Part 1: Nghe 1–5 (6 hình 0..5) & 6–10 (5 hình 6..10)
    plan.append({
        "part": 1,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [0, 1, 2, 3, 4, 5])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：喂，请问张经理在吗？\n女：他正在开会，您半个小时以后再打，好吗？", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：下了飞机，就给我来电话。\n男：好的。你到中国以后，自己照顾好自己。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：请问，二零四房间在哪儿？\n女：请这边走，前面左边第二个就是。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：眼药水用了吗？有作用没？\n男：有作用，现在眼睛已经不红了。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：这些书我可以借多长时间？\n女：一个月。如果看不完，可以再借一个月。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：这张画是你画的吗？\n男：是我爷爷画的，这是他的一张花鸟画。", "dap_an_thu_tu": 1}, False],
        ],
    })
    plan.append({
        "part": 1,
        "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_img(slug, [6, 7, 8, 9, 10])},
        "children": [
            [{"dang": "chon_bo_chung", "loi_nghe": "男：你不舒服吗？要不要我带你去医院检查检查？\n女：没关系，我应该是感冒了，有点儿发烧。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：今天的鸡蛋面怎么样？\n男：很好吃，我吃饱了。我认为你做饭的水平越来越高了。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：欢迎你来公司工作。\n女：谢谢您！谢谢您给我这个机会，我会努力的。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "女：我马上就到，已经到楼下了。你好，一共多少钱？\n男：三十五块。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "loi_nghe": "男：小姐，这么长您看可以吗？\n女：再短一些吧。夏天到了，头发还是短一点儿好。", "dap_an_thu_tu": 2}, False],
        ],
    })

    # Part 2: Nghe 11–20 (Đúng/Sai ★)
    l2 = [
        (True, True, "★ 他希望自己很健康。", "为了让自己更健康，他每天都花一个小时去锻炼身体。\n★ 他希望自己很健康。"),
        (True, False, "★ 那块儿手表不是他的。", "今天我想早点儿回家。看了看手表，才五点。过了一会儿再看表，还是五点，我这才发现我的手表不走了。\n★ 那块儿手表不是他的。"),
        (False, False, "★ 冬天水果很便宜。", "在这里，冬天的水果虽然比夏天的贵，但是很新鲜。\n★ 冬天水果很便宜。"),
        (False, True, "★ 他现在还不能打篮球。", "太好了！他几乎不敢相信这是真的。医生说他很快就能像以前一样打篮球了。\n★ 他现在还不能打篮球。"),
        (False, False, "★ 儿子比爸爸矮。", "儿子十七岁了，长得很快。去年买的裤子，现在已经不能穿了，现在他和他爸爸一样高了。\n★ 儿子比爸爸矮。"),
        (False, True, "★ 八月十五的月亮大。", "八月十五的晚上，月亮就像一个白色的大盘子，非常漂亮。中国人喜欢在这一天和家里人一起吃饭，一起看月亮。\n★ 八月十五的月亮大。"),
        (False, True, "★ 他现在住在公司附近。", "我搬家了。新的房子虽然小了点儿，但是离公司很近。\n★ 他现在住在公司附近。"),
        (False, False, "★ 女儿喜欢小狗。", "我家有一只小猫，胖胖的，很可爱，女儿经常给它洗澡，特别喜欢和它在一起玩儿。\n★ 女儿喜欢小狗。"),
        (False, True, "★ 老李第一次坐船。", "我看老李的脸色不太好，一问才知道他昨天晚上没睡好觉。他说，他第一次坐船，以为和坐车没什么不同，他现在明白了，差远了。\n★ 老李第一次坐船。"),
        (False, False, "★ 他在黑板上画熊猫。", "把椅子上的铅笔给我，谢谢。耳朵、鼻子都画完了，现在该画这只熊猫的脚了。\n★ 他在黑板上画熊猫。"),
        (False, True, "★ 他的成绩不错。", "早上，我在电子信箱里看到了我的成绩单，我的成绩比过去有了很大提高。今天一天我都很快乐。\n★ 他的成绩不错。"),
        (False, False, "★ 高兴的时候不会哭。", "哭，不一定表示难过，有的人着急的时候会哭，有的人在高兴的时候也会哭。\n★ 高兴的时候不会哭。"),
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
        (False, "A", ["包", "糖", "自行车"],
         "女：谢谢你送我的生日礼物！这个包我非常喜欢。\n男：不客气，祝你生日快乐！\n问：男的送什么礼物了？"),
        (False, "C", ["丈夫和妻子", "校长和老师", "客人和服务员"],
         "男：你好，我住六零七，房间里的空调坏了，你能来看看吗？\n女：好的，先生，对不起，我们马上找人来。\n问：他们最可能是什么关系？"),
        (False, "C", ["完成作业", "打扫厨房", "玩儿游戏"],
         "女：你回来就一直玩儿游戏，作业写完了吗？\n男：我在学校就写完了。\n问：男的正在做什么？"),
        (False, "C", ["他不渴", "咖啡太甜", "哪里都可以"],
         "男：奇怪，我记得这条街上有一个咖啡馆儿的。\n女：没关系，我们找个地方坐坐就行。\n问：女的是什么意思？"),
        (False, "A", ["太胖了", "太瘦了", "太短了"],
         "女：这条裙子去年才买的，今年就不能穿了。\n男：你吃得太多，也不运动，可能又长十斤肉了吧？\n问：女的为什么不能穿那条裙子？"),
        (False, "A", ["商场", "饭店", "电影院"],
         "男：帽子在几层呢？\n女：我看看，一层是家电，二层是衣帽，我们去二层。\n问：他们现在在哪儿？"),
        (False, "B", ["很生气", "是经理", "买了个照相机"],
         "女：再见，一会儿你离开的时候记得关灯。\n男：好的，经理，明天见。\n问：关于女的，可以知道什么？"),
        (False, "A", ["姐姐", "妹妹", "邻居"],
         "男：姐，您做的蛋糕真好吃！\n女：洗手了吗？先去把手洗了，然后帮我拿碗筷，准备吃饭。\n问：蛋糕是谁做的？"),
        (False, "A", ["很不错", "有点儿旧", "不太干净"],
         "女：这件衬衫是很好，就是太贵了。\n男：那我再给您便宜五十块，怎么样？\n问：这件衬衫怎么样？"),
        (False, "C", ["喜欢音乐", "没什么爱好", "男朋友影响了她"],
         "男：你怎么突然开始关心体育了？\n女：我的男朋友喜欢看足球比赛，是他影响了我。\n问：女的主要是什么意思？"),
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
        (False, "A", ["超市", "银行", "办公室"],
         "男：喂，请问小李在家吗？\n女：他出去了，请问您是哪位？\n男：我姓王，是他的同学。他什么时候回来？\n女：他去超市买点儿东西，可能十分钟就回来了。\n问：小李现在最可能在哪儿？"),
        (False, "B", ["9：15", "9：45", "10：15"],
         "女：我们这儿有个西瓜文化节，您有兴趣去看看吗？\n男：当然有兴趣了。\n女：我们可以一边吃西瓜一边看表演。\n男：好，现在差一刻十点，我们现在去？\n问：现在几点了？"),
        (False, "A", ["看不懂", "比较简单", "很有意思"],
         "男：你把我的那本书放哪儿了？\n女：在桌子上吧。\n男：我要去还书，今天是最后一天，今天必须还。\n女：还了吧，那本书我也没看懂。\n问：女的觉得那本书怎么样？"),
        (False, "B", ["游客", "出租车司机", "公共汽车司机"],
         "女：你好，我去世界公园。\n男：好的，没问题。\n女：从这儿到世界公园远吗？需要多长时间？\n男：不是很远，半个小时吧。\n问：男的是做什么的？"),
        (False, "A", ["非常聪明", "借了几本书", "想看历史书"],
         "男：你知道的怎么这么多，真聪明！\n女：那是因为我看的书多，读书使人聪明。\n男：那你对历史书也了解不少吧，给我介绍几本？\n女：明天吧？我给你写一个单子。\n问：关于女的，可以知道什么？"),
        (False, "C", ["一米八", "一米八一", "一米八二"],
         "女：小王，你现在有多高？\n男：一米八二。您儿子呢？他比我高？\n女：他可能比你低一点儿。\n男：那也有一米八，很高了。\n问：男的有多高？"),
        (False, "B", ["刷牙", "回答问题", "教学生数学"],
         "男：你叫什么名字？\n女：我叫李静。\n男：请坐，不用站着。你会回答刚才的那个问题吗？\n女：我觉得应该是新年。\n问：女的在做什么？"),
        (False, "C", ["办公楼", "校医院", "图书馆"],
         "女：图书馆在哪儿？\n男：我看看这张校园地图。\n女：图书馆，在这儿，在办公楼的下面。\n男：知道了，我们从办公楼向南走就是图书馆。\n问：他们要去哪儿？"),
        (False, "B", ["跳舞", "照片", "练习题"],
         "男：上次你们参加表演的照片，我选了几张洗出来了。\n女：太好了，我看看。\n男：照得不错，你们都是一个年级的？\n女：不是，这两个大笑的是二年级的，这个是我们班的。\n问：他们在说什么？"),
        (False, "B", ["山高900米", "9月9日爬山", "山上有9个太阳"],
         "女：这个山我来过很多次了，但还不知道它叫什么山。\n男：它叫“九日山”。\n女：为什么叫这个名字呢？\n男：以前，九月九人们都要来这儿爬山。\n问：它为什么被叫做“九日山”？"),
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
                "有不清楚的地方，大家可以问我。",
                "遇到问题时不要太着急。我觉得李阿姨一定可以帮我们的忙。",
                "晚上开车，来杯茶或者苹果汁吧。",
                "图书馆里比较安静，我喜欢在那儿学习。",
                "当然。我们先坐公共汽车，然后换地铁。",
                "别看了，把电视关了吧，明天还要上班呢。",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "你知道怎么去那儿吗？", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "她的习惯和我们不一样，她更愿意去教室。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "菜点完了，你想喝点儿什么？啤酒？", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "你有什么好办法吗？你快想想！", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "马上，这个节目还有10分钟就结束了。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "昨天课上讲的那些题，你们会做了吗？", "dap_an_thu_tu": 1}, False],
        ],
    })
    plan.append({
        "part": 5,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text([
                "已经都解决了，校长，您放心吧。",
                "一起去踢足球，好不好？",
                "冰箱里还有不少香蕉和葡萄呢。",
                "小王没来？打他电话怎么一直没人接？",
                "我们是经过同事介绍认识的，已经认识两年了。",
            ]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "他女朋友比他大一岁，很可爱，而且很聪明。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "奶奶，家里是不是没水果了？", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "上次会上说到的那些问题怎么样了？", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "你等我一下，我去换一双鞋就来。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "他去火车站了，我刚才在电梯门口看见他了。", "dap_an_thu_tu": 4}, False],
        ],
    })

    # Part 6: Đọc 51–55 & 56–60 (Điền từ)
    plan.append({
        "part": 6,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text(["简单", "举行", "像", "复习", "声音", "附近"]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "她说话的（　）多好听啊！", "dap_an_thu_tu": 5}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "有些事情看上去很（　），但要做好，其实不容易。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "听张先生说，机场（　）那个宾馆的环境不错。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "那个会议要在我们学校（　），所以老师们最近特别忙。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "她和她妈妈长得真（　）啊！", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "明天上午考数学，你（　）得怎么样了？", "dap_an_thu_tu": 4}, False],
        ],
    })
    plan.append({
        "part": 6,
        "group": {
            "dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
            "phuong_an": opts_text(["终于", "普通话", "满意", "爱好", "骑", "一会儿"]),
        },
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "A：你有什么（　）？\nB：我喜欢体育。", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "A：怎么样，这房子您还（　）吧？\nB：很不错，但我还想看看其他的。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：照片上（　）马的这个人是你爸爸？\nB：是的，那时他刚参加工作，很年轻。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：儿子，快起床，外面天气非常好，我们出去跑跑步。\nB：今天是周末，您让我再睡（　）吧。", "dap_an_thu_tu": 6}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：他的（　）说得真好。\nB：当然了，你不知道？他是北京人。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：8年了，她（　）同意跟我结婚了。\nB：真的吗？太好了！我真为你高兴！", "dap_an_thu_tu": 1}, False],
        ],
    })

    # Part 7: Đọc 61–70
    r3 = [
        (True, "C", ["8点", "8点半", "9点"], "您是来参加今天会议的吗？您来早了一点儿，现在才八点半。您先进来坐吧。\n★ 会议最可能几点开始？"),
        (False, "C", ["迟到了", "忘记拿机票了", "找不到护照了"], "到了机场，他发现护照不见了，在行李箱里找了半天，也没找到，很着急。\n★ 他为什么着急？"),
        (False, "C", ["要相信别人", "兴趣最重要", "努力才有希望"], "人们经常说：“面包会有的，牛奶也会有的。”是的，如果努力，什么都会有的。\n★ 这句话主要想告诉我们："),
        (False, "B", ["去医院", "锻炼身体", "下午去游泳"], "上个星期和朋友们去游泳，把我累坏了，到现在我的腿还在疼。看来我是应该多锻炼锻炼了。\n★ 他打算："),
        (False, "C", ["今天是阴天", "现在是秋季", "他来过这儿"], "越高的地方越冷，山路也越难走。但是不用担心，有我呢，我去年秋天爬过这个山，这儿我还是比较了解的。我饿了，我们先坐下来吃点儿饭、喝点儿水，然后再爬。一会儿我们可以从中间这条路上去。\n★ 根据这段话，可以知道什么？"),
        (False, "B", ["热极了", "变化快", "一般不下雨"], "“6月的天，孩子的脸，说变就变。”刚才还是大晴天，现在就要用伞了。雨越下越大，天也变得越来越黑，街上一辆出租车也打不到了。\n★ 6月的天气："),
        (False, "B", ["老朋友", "不认识的字", "爱好相同的人"], "看书时会遇到一些历史上的人或者国家的名字，这些字现在很多都不用了，想要知道它们的读音和意思，还需要词典的帮助，所以有本词典很方便。\n★ 看书时会遇到："),
        (False, "C", ["做米饭", "坐地铁", "买东西"], "过去人们喜欢看报纸，现在越来越多的人喜欢在电脑上看新闻。除了看新闻，人们还可以在网上听歌、看电影、买卖东西。\n★ 上网后，人们可以："),
        (False, "A", ["6分", "5角", "2元"], "超市里一箱牛奶如果卖32.56元，也就是32块5角6分，那可能会带来许多不方便，因为现在人们的钱包里很少有“分”这么小的零钱。\n★ 人们的钱包里很少有："),
        (False, "A", ["爱听故事", "变化很大", "害怕一个人睡觉"], "每天睡觉前，女儿总会要求妈妈给她讲一个故事，开始的时候她听得很认真，慢慢地就睡着了。\n★ 根据这段话，女儿："),
        (False, "B", ["经常刮风", "环境很好", "人们很热情"], "那个地方很有名，蓝天，白云，绿草，很多人喜欢去那里旅游。我哥哥家就住在那儿，他们家旁边有一条小河，河边有高高的树，河里游着一种黄色的小鱼。\n★ 那个地方怎么样？"),
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
        (False, ["送给", "她决定", "把手机", "弟弟"], ["她决定把手机送给弟弟。"]),
        (False, ["见面", "没", "我和这个学生", "很久", "了"], ["我和这个学生很久没见面了。"]),
        (False, ["经常", "的", "春天", "刮风", "这个城市"], ["这个城市的春天经常刮风。"]),
        (False, ["他的汉字", "写", "很漂亮", "得"], ["他的汉字写得很漂亮。"]),
        (False, ["花了", "叔叔的", "900块钱", "太阳镜"], ["叔叔的太阳镜花了900块钱。"]),
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
        (False, "4（ yuè ）7号是我的生日，中午你们来我家吃饭吧。", ["月"]),
        (False, "看地图？很容易，上北、下南、左西、右东，明（ bai ）了？", ["白"]),
        (False, "一（ qiān ）万年前，动物们出现了吗？", ["千"]),
        (False, "外面下雪了，你让孩子路上小（ xīn ）点儿。", ["心"]),
        (False, "生病了要注意休息，（ yīn ）为健康最重要。", ["因"]),
    ]
    for ex, s, acc in w2:
        plan.append({
            "part": 9, "ex": ex,
            "q": {"dang": "dien_chu", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "goi_y": "Điền chữ Hán theo pinyin trong ngoặc", "dap_an_chap_nhan": acc},
        })

    return {
        "exam": {
            "code": "H31003",
            "level": "HSK3",
            "ten": "HSK 3 – Đề 3",
            "phut": 90,
            "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（三级）H31003",
            "audio": f"exams/{slug}/listening.mp3",
            "img_dir": f"exams/{slug}/img",
        },
        "plan": plan,
    }


# ==============================================================================
# 3. HSK 4 – Đề 3 (H41003) — 100 câu tính điểm + 10 câu ví dụ
# ==============================================================================
def build_h41003() -> dict:
    slug = "hsk4_h41003"
    img = lambda n: f"exams/{slug}/img/{n:03d}.jpg"
    plan = []

    # Part 1: Nghe 1–10 (Đúng/Sai ★)
    l1 = [
        (True, True, "★ 他打算下午去银行。", "我想去办个信用卡，今天下午你有时间吗？陪我去一趟银行？\n★ 他打算下午去银行。"),
        (True, False, "★ 他喜欢看电视广告。", "现在我很少看电视，其中一个原因是，广告太多了，不管什么时间，也不管什么节目，只要你打开电视，总能看到那么多的广告，浪费我的时间。\n★ 他喜欢看电视广告。"),
        (False, True, "★ 他想买蛋糕。", "对不起，先生，那种蛋糕已经卖完了，不过，您可以尝一下这种饼干，味道也很不错。\n★ 他想买蛋糕。"),
        (False, True, "★ 他现在住的地方很安静。", "我挺喜欢现在住的地方，很安静。不像以前住的地方，虽然交通方便，但是周围很吵。\n★ 他现在住的地方很安静。"),
        (False, False, "★ 大学生不愿意去农村工作。", "虽然很多大学生毕业后希望留在大城市工作，但也有不少大学生选择去农村，因为在那里也有许多好的发展机会。\n★ 大学生不愿意去农村工作。"),
        (False, False, "★ 会议室在二层。", "您是要去会议室吗？那不用上楼，会议室就在一层。您往前走，就在电梯左边。\n★ 会议室在二层。"),
        (False, True, "★ 参观时间是一小时。", "现在是九点半，请大家注意：一小时后我们还在这个入口集合，参观过程中请大家注意安全。\n★ 参观时间是一小时。"),
        (False, False, "★ 超市提供免费塑料袋。", "因为塑料袋会给环境带来污染，所以现在超市不再免费提供塑料袋，有需要的顾客，可以向超市购买。\n★ 超市提供免费塑料袋。"),
        (False, False, "★ 海洋里的植物很少。", "和森林一样，在海洋里，也生长着很多种植物，它们与海洋里的动物，共同组成了一个美丽的海底世界。\n★ 海洋里的植物很少。"),
        (False, False, "★ 他的职业是演员。", "我父亲是医生，母亲是演员。我的性格很像我父亲，我的理想就是做一个像父亲那样的医生。\n★ 他的职业是演员。"),
        (False, True, "★ 他下周回来。", "张记者，我刚刚接到通知，明天要出差，恐怕没时间和您见面了。很抱歉，等我回来以后再跟您联系，我下周一回来。\n★ 他下周回来。"),
        (False, True, "★ 习惯很难改变。", "习惯是不容易改变的，因此，在孩子小的时候，父母要帮他们养成好的生活、学习习惯。\n★ 习惯很难改变。"),
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
        (False, "C", ["迟到了", "不能上网了", "房子不租了", "打错电话了"], "男：喂，你好，我在网上看到你们的广告，你有房子要出租是吗？\n女：实在对不起，那个房子暂时不租了，对不起。\n问：女的为什么表示抱歉？"),
        (False, "C", ["加班", "出差", "休息", "购物"], "女：明天周末了，你有什么安排吗？\n男：我刚出差回来，有点儿累，就想在家里休息休息。\n问：男的周末准备做什么？"),
        (False, "B", ["做汤", "做凉菜", "做饮料", "加点儿盐"], "男：这几个西红柿怎么吃？\n女：就加点儿糖，做个凉菜吧。\n问：女的打算怎么吃？"),
        (False, "A", ["教师", "大夫", "律师", "售货员"], "女：真羡慕你，除了平时的节假日，还有一个寒假和一个暑假。\n男：当时选择这个职业，没考虑到这些，我只是喜欢和孩子们在一起。\n问：男的最可能是做什么的？"),
        (False, "C", ["太远", "菜贵", "菜好吃", "菜很咸"], "男：那个饭店离咱们家也太远了，我们就在附近吃吧。\n女：不算太远。它的菜做得很好吃，而且价格也不贵。\n问：女的觉得那家饭店怎么样？"),
        (False, "B", ["10分钟", "半个小时", "一个小时", "一个半小时"], "女：导游刚才说还要多久才能到长城？\n男：还有半小时就到了，我本来以为还得一个小时呢。\n问：到长城还要多长时间？"),
        (False, "D", ["帅的", "耐心的", "诚实的", "幽默的"], "男：你为什么不喜欢小王？他不是挺成熟的吗？\n女：可是他一点儿也不幽默，约会的时候真无聊。\n问：女的喜欢什么样的人？"),
        (False, "A", ["要办签证", "是位翻译", "要办护照", "在使馆工作"], "女：小王，我要去办签证，需要准备哪些材料？\n男：我也不是很清楚，我有大使馆的号码，您给他们打个电话问问？\n问：关于女的，可以知道什么？"),
        (False, "C", ["艺术", "经济", "法律", "语言"], "男：你怎么懂这么多法律知识？\n女：我研究生读的就是法律专业啊，你不知道？\n问：女的熟悉哪方面的知识？"),
        (False, "D", ["兴奋", "吃惊", "轻松", "着急"], "女：怎么样？那个技术上的问题解决了吧？\n男：我以为今天能顺利解决，但是情况比我想的复杂得多，怎么办呢？\n问：男的现在心情怎么样？"),
        (False, "A", ["开会", "报名", "上课", "看电影"], "男：以上是这次活动的计划，看看大家还有什么意见。\n女：我觉得安排得很好，由你来组织我们都很放心。\n问：他们最可能在做什么？"),
        (False, "C", ["饿了", "感冒了", "流鼻血了", "压力太大"], "女：你的鼻子怎么流血了？快用纸擦擦。\n男：我还不习惯北方的气候，估计是天气太干燥。\n问：男的怎么了？"),
        (False, "A", ["来得及", "来不及了", "速度太慢了", "航班推迟了"], "男：只剩下十五分钟，今天恐怕要迟到了。\n女：别担心，现在不堵车，十五分钟肯定够。\n问：女的主要是什么意思？"),
        (False, "C", ["司机", "经理", "小李", "护士"], "女：经理，我想把这个任务交给小李，您看合适不合适？\n男：他有能力也有责任心，虽然经验不多，但可以让他试试。\n问：谁缺少经验？"),
        (False, "D", ["不成功", "让人失望", "比较一般", "很吸引人"], "男：昨天下午的演出怎么样？\n女：你没有和我一起去看真是太可惜了。\n问：女的觉得表演怎么样？"),
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
        (False, "A", ["同事", "邻居", "夫妻", "亲戚"], "女：你一个人对着手机笑什么？\n男：我妹刚发来一个笑话，你看看，笑死我了。\n女：这么好笑？那你也给我发一个。\n男：好的，我给咱办公室的同事都发一遍。\n问：他们是什么关系？"),
        (False, "D", ["历史", "长度", "风景", "经过的省市"], "男：姐，您这儿有中国地图吗？\n女：没有，你要地图做什么？\n男：我想看看长江都经过了哪些省市，你知道吗？\n女：真笨！上网一查不就知道了吗？\n男：那不一样。\n问：男的想了解长江的什么？"),
        (False, "A", ["太累", "得意", "感动", "怀疑"], "女：我们去对面的商店看看吧。\n男：我真的受不了你了，你到底还要逛多久？\n女：我们才逛了一个小时。\n男：时间过得真慢，和你逛街比上班还辛苦。\n问：男的现在是什么感觉？"),
        (False, "A", ["在读博士", "在读硕士", "在找工作", "想出国留学"], "男：见到你真高兴！你已经硕士毕业了吧？\n女：是的，我去年就毕业了。\n男：那你现在在哪儿工作呢？\n女：我还没参加工作呢，毕业后直接读博士了。\n问：关于女的，可以知道什么？"),
        (False, "D", ["8：00", "8：30", "9：00", "9：30"], "女：你好，我是前台。\n男：你好，我住八零七。楼下现在还有早饭吗？\n女：对不起，早饭提供到九点。\n男：明白了。谢谢你。\n问：现在最可能是几点？"),
        (False, "A", ["想减肥", "想聊天", "停电了", "电梯坏了"], "男：我们爬到六层了，可以了吧？\n女：不行，要爬到十四层，这样才有效果。\n男：啊，可是我现在就没力气了。\n女：想减肥就要坚持！我们先休息休息再爬。\n问：他们为什么爬楼梯？"),
        (False, "B", ["家里", "商场", "教室", "银行"], "女：咱家的洗衣机坏了，商场正好打折，我们顺便买一台吧。\n男：今天买的东西太多了，钱不够了，下次再说？\n女：我带着信用卡呢，给你。\n男：好吧。\n问：他们现在在哪儿？"),
        (False, "D", ["2500", "3000", "3200", "3500"], "男：你看，这个怎么样？图书馆招聘人。\n女：在哪儿？我看看。\n男：好像挺适合你的。\n女：三千五？工资还挺高，那我先发个电子邮件吧。\n问：这个工作的工资是多少？"),
        (False, "B", ["请不了假", "害怕打针", "讨厌吃药", "肚子不疼了"], "女：你的咳嗽怎么一直没好？去医院看看吧。\n男：不去，不是很严重，吃点药就行了。\n女：关键是你吃了药也没好呀。\n男：不去。我跟你说，其实我是怕打针。\n问：男的为什么不去医院？"),
        (False, "A", ["同意", "原谅", "太麻烦", "十分满意"], "男：这些塑料盒子还有用吗？\n女：没用了。\n男：没用的东西就放垃圾桶里，别到处乱扔。\n女：好吧，那我现在把房间整理一下。\n问：女的是什么态度？"),
    ]
    for ex, ans, op, said in l3_single:
        plan.append({
            "part": 3, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(op, ans)},
        })

    l3_groups = [
        ("有个人出名之前，穿得很随便。朋友对他说，应该买件漂亮的大衣。他笑着回答：“我本来就没有名，穿得再漂亮也没有人会认识。”几年后，出了名的他穿得仍然很随便。朋友又提醒他，快去做件漂亮的大衣。他还是笑着回答：“现在即使穿得更随便些，同样也会有人认识我。”",
         [("朋友对他说什么了？", "B", ["不要骄傲", "买件大衣", "要努力工作", "别忘了过去"]),
          ("关于那个人，可以知道什么？", "D", ["很活泼", "后来很穷", "喜欢弹钢琴", "成为了名人"])]),
        ("各位观众，大家晚上好。欢迎大家在星期六晚上，准时收看我们的《人与自然》节目。在今天的节目里，我们主要向大家介绍亚洲虎。今天我们还请来了国内著名的动物学教授，王教授，来给我们介绍这方面的知识。",
         [("今天星期几？", "D", ["星期三", "星期四", "星期五", "星期六"]),
          ("今天的节目主要介绍什么？", "C", ["亚洲", "地球", "老虎", "狮子"])]),
        ("阳光能给我们带来好的心情。当你心情不好的时候，如果天也在下雨，你的脾气很容易变得更坏。相反，如果天气很好，有阳光，你就容易看到事情好的方面，心情也就会变得好起来。",
         [("阳光能给我们带来什么？", "D", ["爱情", "烦恼", "友谊", "好心情"]),
          ("这段话主要谈什么？", "D", ["环境污染", "天气情况", "身体健康", "阳光影响心情"])]),
        ("在乘坐地铁和公共汽车等交通工具时，经常可以听到这样的广播：“下一站就要到了，请下车的乘客提前做好准备。”按照广播的提醒到车门旁边等着下车，既方便了自己，也方便了他人。",
         [("广播提醒乘客什么？", "B", ["主动买票", "准备下车", "带好行李", "禁止抽烟"]),
          ("在哪儿能听到这样的广播？", "D", ["船上", "飞机上", "出租车上", "公共汽车上"])]),
        ("很多女孩子羡慕小说里浪漫、复杂的爱情，认为经历了酸甜苦辣的爱情才算是深厚的。其实，更值得我们重视和尊重的，正是实际生活中简单的爱情。有时候，简单就是最大的幸福。",
         [("女孩子为什么喜欢小说里的爱情？", "A", ["很浪漫", "值得同情", "特别有趣", "内容丰富"]),
          ("说话人认为什么样的爱情才是幸福的？", "B", ["精彩的", "简单的", "相互信任的", "勇敢去爱的"])]),
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
                  "phuong_an": opts_text(["食品", "粗心", "礼貌", "坚持", "挂", "完全"])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "她每天都（　）走路上下班，所以身体一直很不错。", "dap_an_thu_tu": 4}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "她要求在洗手间的墙上（　）一面大镜子。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "他弟弟不但聪明，而且很懂（　），给客人们留下了非常好的印象。", "dap_an_thu_tu": 3}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "不管做什么事情，都应该认真、仔细，不能太马虎、太（　）。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "小姐，这边都是（　），毛巾、牙膏什么的在那边，右边。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "市场调查结果和他们想的几乎（　）相反，他们不得不改变原来的计划。", "dap_an_thu_tu": 6}, False],
        ],
    })
    plan.append({
        "part": 4,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(["最好", "继续", "温度", "热闹", "作者", "商量"])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "A：今天真冷啊，好像白天最高（　）才2℃。\nB：刚才电视里说明天更冷。", "dap_an_thu_tu": 3}, True],
            [{"dang": "chon_bo_chung", "noi_dung": "A：那篇文章的（　）是谁？\nB：我忘了他叫什么名字了，只记得他姓李。", "dap_an_thu_tu": 5}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：外面有好多人，停了好多辆车，特别（　）。\nB：今天老王的女儿结婚，我们也去祝贺一下吧。", "dap_an_thu_tu": 4}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：咱们把沙发往窗户那儿抬一下，这样看电视更舒服些。\nB：别开玩笑了，我们俩抬不动，（　）等你爸爸回来再弄。", "dap_an_thu_tu": 1}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：所有的困难都是暂时的，要有信心，我相信你会成功的。\nB：感谢您的支持和鼓励，我一定会（　）努力。", "dap_an_thu_tu": 2}, False],
            [{"dang": "chon_bo_chung", "noi_dung": "A：这事你跟她（　）了吗？\nB：还没，她最近在忙公司的事情，我怕打扰她。", "dap_an_thu_tu": 6}, False],
        ],
    })

    # Part 5: Đọc 56–65 (Sắp xếp A, B, C)
    r2 = [
        (True, "BAC", ("可是今天起晚了", "平时我骑自行车上下班", "所以就打车来公司")),
        (False, "BCA", ("带来一天的好心情", "一个笑话", "也许就能带走我们的烦恼")),
        (False, "CBA", ("就可以变得越来越优秀", "但只要能发现自己的缺点并及时去改", "每个人都有缺点")),
        (False, "ACB", ("平时，儿子总是在学校上课", "只有放了假，才有可能和我们一块儿去旅游", "学习很紧张，很少有时间出去玩儿")),
        (False, "CBA", ("因为无论成功还是失败，努力过的人都应获得掌声", "当然，也不要忘了鼓励那些失败的人", "我们要为那些通过自己努力获得成功的人鼓掌")),
        (False, "BAC", ("所以对我来说，年龄只是一个数字", "我的理解是，重要的是要有永远年轻的心", "我从来不关心它")),
        (False, "BCA", ("在原有的基础上，增加了一部分文化交流的内容", "王校长，根据您的要求", "我把这篇报道稍微改了一下")),
        (False, "ABC", ("放弃并不代表认输，而是代表新的开始", "因此，为了获得更多", "需要主动丢掉一些不重要的东西")),
        (False, "CAB", ("人就容易梦到什么内容", "例如，一个人脚冷时就可能会梦见在雪地里行走", "晚上睡觉时，身体感觉到什么")),
        (False, "ACB", ("我打算毕业以后", "为将来自己做生意积累一些管理经验", "先在叔叔开的公司里干一段时间")),
        (False, "ACB", ("她是我的同学，从小就想成为一名警察", "现在她决定，一定要找一个警察做丈夫", "然而由于种种原因，她没能当上警察")),
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
        (True, "A", ["幽默", "马虎", "骄傲", "害羞"], "她很活泼，说话很有趣，总能给我们带来快乐，我们都很喜欢和她在一起。\n★ 她是个什么样的人？"),
        (False, "C", ["更节约", "拒绝变化", "关心将来", "缺少竞争力"], "老人总是喜欢往回看，回忆总结自己过去的经历；而年轻人却相反，他们喜欢向前看，也容易接受新鲜事情。\n★ 和老年人相比，年轻人："),
        (False, "B", ["年龄大", "会解决问题", "不会做错事", "不会遇到问题"], "一个人成熟不成熟，不是看年龄的大小，而是要看他遇到问题时，能不能及时发现，并且准确地找到解决问题的方法。\n★ 成熟的人有什么特点？"),
        (False, "C", ["很便宜", "很普通", "质量不错", "数量很少"], "这个公司专门制造各种各样的筷子。他们的筷子用不同的材料做成，颜色也都不一样，质量很好。买来不仅可以自己用，还可以当礼物送给别人，顾客们都很喜欢。\n★ 这个公司制造的筷子："),
        (False, "C", ["后悔了", "很生气", "想换专业", "成绩不合格"], "既然你不喜欢新闻专业，那就再考虑考虑其他专业吧，中文、国际关系什么的，妈和你爸都不反对。但是为了将来不后悔，不要这么快做决定，至少应该去了解一下这个专业，也许最后你会改变主意的。\n★ 根据这段话，可以知道他："),
        (False, "A", ["尊重别人", "多与人交流", "多表扬别人", "严格要求自己"], "要获得别人的尊重，必须先尊重别人。任何人心里都希望获得尊重，受到尊重的人往往会变得更友好、更容易交流。\n★ 怎样获得别人的尊重？"),
        (False, "C", ["正式的", "高级的", "适合自己的", "人们普遍接受的"], "有不少人都喜欢按照流行的标准来穿衣服、打扮自己。其实，是不是流行不重要，真正适合自己的才是最好的。\n★ 年轻人应该穿什么样的衣服？"),
        (False, "C", ["减少降雨", "降低气温", "使空气湿润", "使降雪受到限制"], "森林对环境有很好的保护作用。因为森林里的植物可以留住更多的水，使空气变得湿润，还可以影响地球的温度。\n★ 森林对保护环境有什么作用？"),
        (False, "B", ["条件", "原因", "办法", "重点"], "网球爱好者都知道，选择厚一点儿的网球袜确实更好。第一，它能很好地吸汗，尤其适合那些容易出汗的人。第二，在紧张的运动过程中，厚的网球袜能更好地保护你的脚。\n★ 这段话主要讲了选择厚网球袜的："),
        (False, "B", ["还书", "找他的包", "表示道歉", "重新申请奖学金"], "3月7日上午，我在体育馆打羽毛球时，丢了一个咖啡色书包，里面有笔记本电脑、钥匙和几本杂志，请拿到包的人与我联系。非常感谢。\n★ 这个人写这段话的目的是："),
        (False, "A", ["学习骑马", "偶尔去散步", "邀请朋友做客", "参加跳舞比赛"], "当地少数民族朋友不仅主动邀请我们去他们家做客，还教我们骑马、唱民歌，那儿的人可爱极了。\n★ 我们在当地："),
        (False, "D", ["很奇怪", "很冷静", "极其可怜", "有好的习惯"], "有一个人去公司面试时，顺手把地上的香蕉皮扔进了垃圾桶，正好被路过的经理看见了，因此他得到了工作。\n★ 经理觉得那个人怎么样？"),
        (False, "D", ["更干净", "座位更软", "速度更快", "火车站比机场近"], "现在火车的速度非常快，有时乘坐火车甚至比乘坐飞机更节约时间，因为一般来说，去火车站比去机场的距离要近得多。\n★ 与飞机比，火车的优点有："),
        (False, "B", ["太复杂", "不安全", "会引起误会", "很浪费时间"], "人脑不是电脑，所以密码不能太复杂，不过也不能太简单，否则不安全。想要密码安全，最好不要用手机号码、生日等。\n★ 用手机号码做密码："),
        (False, "C", ["很窄", "有很多座桥", "从西流向东", "大约一万多公里"], "黄河是中国第二大河，从中国西部流向东部，全长5464公里，被人们叫做“母亲河”。从地图上看，它就像一个大大的“几”字。\n★ 关于黄河，可以知道："),
    ]
    for ex, ans, op, s in r3_single:
        plan.append({
            "part": 6, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "phuong_an": opts_text(op, ans)},
        })

    r3_groups = [
        ("教育孩子要使用正确的方法。首先，不要用“懒”“笨”“粗心”这种词批评孩子，这样很容易让他们相信自己就是那样的，于是限制了他们正常的发展。其次，即使是出于教育的目的，也千万不能骗孩子，因为儿童缺少判断能力，看到父母骗人，他们也会学着说假话。",
         [("★ 批评孩子懒、笨、粗心，会让孩子：", "C", ["说假话", "缺少判断力", "发展受到限制", "不敢相信任何人"]),
          ("★ 这段话主要讲怎样正确：", "B", ["批评孩子", "教育孩子", "照顾孩子", "帮助孩子"])]),
        ("医生对一个很胖的人说如果他每天跑8公里，跑300天，差不多就能减34公斤。300天后，医生接到那个人的电话，说他已经减了34公斤，但他因此也有了个难题，“什么难题？”医生问。那人说：“我现在已经离家2400公里了。”",
         [("★ 那个人每天跑步是因为：", "A", ["太胖了", "想赢比赛", "想赚更多的钱", "想引起别人注意"]),
          ("★ 300天后，那个人的难题是什么？", "C", ["没成功", "太瘦了", "离家太远", "不适应家里的生活"])]),
        ("科学研究证明，颜色会影响人的心情，不同的颜色会给人带来不同的感情变化。红色会让人变得热情，使人兴奋；黄色和白色让人觉得心情愉快，给人带来快乐；黑色却容易让人感到伤心难过；人们在看到蓝色时会觉得很舒服，会变得安静下来；绿色会让我们的眼睛得到休息，对我们的身体也有好处。",
         [("★ 根据这段话，哪种颜色会让人觉得难受？", "B", ["白色", "黑色", "黄色", "蓝色"]),
          ("★ 这段话主要谈颜色：", "D", ["的区别", "的故事", "对眼睛的好处", "与心情的关系"])]),
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
        (False, ["爷爷", "非常", "感兴趣", "对", "京剧"], ["爷爷对京剧非常感兴趣。"]),
        (False, ["请", "那张表格", "把", "两份", "打印"], ["请把那张表格打印两份。"]),
        (False, ["很详细", "这个传真机的", "写", "得", "说明书"], ["这个传真机的说明书写得很详细。"]),
        (False, ["2009年7月8号", "我孙子", "是", "出生的"], ["我孙子是2009年7月8号出生的。"]),
        (False, ["亿元", "许多家饭店的", "都超过了", "年收入"], ["许多家饭店的年收入都超过了亿元。"]),
        (False, ["保证", "我", "完成", "按时", "任务"], ["我保证按时完成任务。"]),
        (False, ["这个", "没有", "语法错误", "句子"], ["这个句子没有语法错误。"]),
        (False, ["马上", "结束了", "就要", "这场足球赛"], ["这场足球赛马上就要结束了。", "马上这场足球赛就要结束了。"]),
        (False, ["不知道", "难道你", "连这个规定", "都"], ["难道你连这个规定都不知道？"]),
        (False, ["顺利", "祝", "你们", "这次访问", "一切"], ["祝你们这次访问一切顺利。"]),
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
        (False, 1, "收拾", "她每天都要收拾房间。"),
        (False, 2, "理发", "他喜欢去那儿理发。"),
        (False, 3, "困", "困了就休息一下吧。"),
        (False, 4, "激动", "这个消息让他非常激动。"),
        (False, 5, "讨论", "他们正在讨论那个计划。"),
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
            "code": "H41003",
            "level": "HSK4",
            "ten": "HSK 4 – Đề 3",
            "phut": 105,
            "nguon": "国家汉办/孔子学院总部 – 新汉语水平考试 HSK（四级）H41003",
            "audio": f"exams/{slug}/listening.mp3",
            "img_dir": f"exams/{slug}/img",
        },
        "plan": plan,
    }


def main() -> int:
    specs = [
        ("hsk2_h21003.json", build_h21003()),
        ("hsk3_h31003.json", build_h31003()),
        ("hsk4_h41003.json", build_h41003()),
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
