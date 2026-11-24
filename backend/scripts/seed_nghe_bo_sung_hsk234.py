"""Hoàn thiện Bài 4 và Kiểm tra cuối thửa (vị trí 4 & 5) cho các thửa Nghe HSK 2, HSK 3, HSK 4.

Trước đây mỗi thửa Nghe HSK 2–4 chỉ có Bài 1–3 (15 câu), khiến học viên không thể làm Kiểm tra cuối thửa để
thu hoạch thửa hoặc mở Vượt chặng. Kịch bản này tạo thêm 10 câu Nghe mới/cấp (tổng 30 tệp âm thanh đa giọng thật)
kèm Gợi ý 2 mức, đăng Bài 4 (5 câu mới) và Kiểm tra cuối thửa (5 câu mới + 5 câu tổng hợp từ Bài 1–3 = 10 câu).
An toàn khi chạy lại nhiều lần (idempotent).
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.exam_authoring.services.ai_media_service import make_audio
from app.modules.practice_authoring.services import path_service
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question


def place(options: list[str], correct_index: int, slot: int) -> tuple[list[str], int]:
    right = options[correct_index]
    others = [o for i, o in enumerate(options) if i != correct_index]
    idx = slot % len(options)
    others.insert(idx, right)
    return others, idx


def mc(opts: list[str], answer: int) -> list[dict]:
    return [{"noi_dung": o, "la_dap_an_dung": i == answer} for i, o in enumerate(opts)]


def q_listen(nhom: str, script: str, stem: str, opts: list[str], dich: str, g1: str, g2: str, gt: str) -> dict:
    return {
        "nhom": nhom,
        "loi_nghe": script,
        "noi_dung": stem,
        "raw_opts": opts,  # index 0 is correct before deterministic shuffle
        "dich_nghia": dich,
        "goi_y": g1,
        "goi_y_2": g2,
        "giai_thich": gt,
    }


SUPPLEMENTS = {
    2: {
        "land_name": "Hội thoại hằng ngày",
        "lesson4_name": "Thời tiết, sức khỏe và sở thích",
        "lesson4_items": [
            q_listen(
                "thoi_gian_lich_hen",
                "男：明天星期六，我们去公园踢足球吧？\n女：天气预报说明天上午有雨，我们改到星期天下午去吧。\n问：他们什么时候去踢足球？",
                "他们什么时候去踢足球？",
                ["星期天下午 [xīngqītiān xiàwǔ]", "星期六上午 [xīngqīliù shàngwǔ]", "今天下午 [jīntiān xiàwǔ]"],
                "Họ khi nào đi đá bóng?\nA/B/C: Chiều Chủ nhật / Sáng thứ Bảy / Chiều hôm nay",
                "Lắng nghe lý do người nữ từ chối sáng thứ Bảy và thời gian hẹn lại sau chữ 改到…",
                "Người nữ nói: 我们改到星期天下午去吧 (đổi sang chiều Chủ nhật).",
                "Sáng thứ Bảy có mưa nên hai người đổi lịch đá bóng sang chiều Chủ nhật (星期天下午).",
            ),
            q_listen(
                "gia_dinh_nghe_nghiep",
                "女：你今天怎么没喝咖啡，改喝热牛奶了？\n男：医生说我最近晚上睡不好，让我少喝咖啡。\n问：男的现在喝什么？",
                "男的现在喝什么？",
                ["牛奶 [niúnǎi]", "咖啡 [kāfēi]", "西瓜汁 [xīguāzhī]"],
                "Người nam hiện đang uống gì?\nSữa bò / Cà phê / Nước ép dưa hấu",
                "Chú ý câu hỏi đầu tiên của người nữ: 改喝…了？",
                "Người nam bỏ cà phê và chuyển sang uống sữa nóng (热牛奶).",
                "Theo lời khuyên của bác sĩ để ngủ ngon hơn, người nam hiện uống sữa bò (牛奶).",
            ),
            q_listen(
                "so_dem_luong_tu",
                "男：这件白毛衣多少钱？\n女：原来两百块，今天商店做活动，只要一百五十块。\n问：这件毛衣今天卖多少钱？",
                "这件毛衣今天卖多少钱？",
                ["一百五十块 [yìbǎi wǔshí kuài]", "两百块 [liǎngbǎi kuài]", "五十块 [wǔshí kuài]"],
                "Chiếc áo len này hôm nay bán giá bao nhiêu?\n150 tệ / 200 tệ / 50 tệ",
                "Phân biệt giá gốc (原来) và giá khuyến mãi hôm nay (今天只要…).",
                "Hôm nay cửa hàng khuyến mãi nên 只要一百五十块 (chỉ 150 tệ).",
                "Giá gốc 200 tệ, hôm nay khuyến mãi còn 150 tệ (一百五十块).",
            ),
            q_listen(
                "vi_tri_phuong_huong",
                "女：请问，这儿离火车站远吗？走路要多久？\n男：不远，从这儿往右走十分钟就到了。\n问：去火车站走路要多长时间？",
                "去火车站走路要多长时间？",
                ["十分钟 [shí fēnzhōng]", "二十分钟 [èrshí fēnzhōng]", "半个小时 [bàn gè xiǎoshí]"],
                "Đi bộ ra ga tàu hỏa mất bao lâu?\n10 phút / 20 phút / Nửa tiếng",
                "Nghe kỹ con số thời gian đi sau cụm 往右走…",
                "Người nam chỉ đường: 往右走十分钟就到了 (đi 10 phút là tới).",
                "Từ đây rẽ phải đi bộ 10 phút (十分钟) là đến ga tàu hỏa.",
            ),
            q_listen(
                "tro_tu_dong_thai",
                "男：小丽，外边下雪了，快多穿一件衣服再出门。\n女：好的，我已经把红大衣穿上了。\n问：外边天气怎么样？",
                "外边天气怎么样？",
                ["下雪了 [xiàxuě le]", "晴天 [qíngtiān]", "非常热 [fēicháng rè]"],
                "Thời tiết bên ngoài như thế nào?\nCó tuyết rơi / Trời nắng / Rất nóng",
                "Chú ý ngay câu mở đầu của người nam báo tin thời tiết bên ngoài.",
                "Người nam nói: 外边下雪了 (bên ngoài tuyết rơi rồi).",
                "Thời tiết bên ngoài đang có tuyết rơi (下雪了).",
            ),
        ],
        "final_new_items": [
            q_listen(
                "bo_ngu",
                "女：昨天的汉语考试题多不多？你做完了吗？\n男：题不少，不过我都做完了，觉得不太难。\n问：男的觉得昨天的考试怎么样？",
                "男的觉得昨天的考试怎么样？",
                ["不太难 [bú tài nán]", "太难了 [tài nán le]", "没做完 [méi zuò wán]"],
                "Người nam cảm thấy bài thi hôm qua thế nào?\nKhông khó lắm / Khó quá / Chưa làm xong",
                "Nghe phần nhận xét cuối câu của người nam.",
                "Người nam nói: 我都做完了，觉得不太难.",
                "Người nam đã làm xong hết đề và thấy bài thi không khó lắm (不太难).",
            ),
            q_listen(
                "gia_dinh_nghe_nghiep",
                "男：照片里穿蓝衣服的女孩儿是你妹妹吗？\n女：不是，那是我哥哥的女儿，今年八岁了。\n问：穿蓝衣服的女孩儿今年几岁？",
                "穿蓝衣服的女孩儿今年几岁？",
                ["八岁 [bā suì]", "六岁 [liù suì]", "十岁 [shí suì]"],
                "Bé gái mặc áo xanh năm nay mấy tuổi?\n8 tuổi / 6 tuổi / 10 tuổi",
                "Lắng nghe số tuổi ở cuối lời thoại của người nữ.",
                "Người nữ giới thiệu cháu gái: 今年八岁了 (năm nay 8 tuổi).",
                "Cô bé mặc áo xanh là con gái của anh trai, năm nay 8 tuổi (八岁).",
            ),
            q_listen(
                "chao_hoi_giao_tiep",
                "女：大卫，你的自行车修好了吗？\n男：还没呢，所以这几天我都坐公共汽车去上班。\n问：大卫这几天怎么去上班？",
                "大卫这几天怎么去上班？",
                ["坐公共汽车 [zuò gōnggòngqìchē]", "骑自行车 [qí zìxíngchē]", "坐出租车 [zuò chūzūchē]"],
                "Mấy hôm nay David đi làm bằng gì?\nĐi xe buýt / Đạp xe đạp / Đi taxi",
                "Xe đạp chưa sửa xong (还没呢), nghe vế sau chữ 所以…",
                "Người nam nói: 所以这几天我都坐公共汽车去上班.",
                "Vì xe đạp chưa sửa xong nên mấy hôm nay David đi xe buýt (坐公共汽车).",
            ),
            q_listen(
                "thoi_gian_lich_hen",
                "男：妈妈，晚饭做好了吗？我饿了。\n女：鱼和米饭好了，再等五分钟把青菜炒完就吃。\n问：他们还要等多久才吃晚饭？",
                "他们还要等多久才吃晚饭？",
                ["五分钟 [wǔ fēnzhōng]", "十五分钟 [shíwǔ fēnzhōng]", "半个小时 [bàn gè xiǎoshí]"],
                "Họ còn phải đợi bao lâu nữa mới ăn tối?\n5 phút / 15 phút / Nửa tiếng",
                "Nghe kỹ cụm 再等… của người mẹ.",
                "Mẹ nói: 再等五分钟把青菜炒完就吃.",
                "Chỉ cần đợi thêm 5 phút (五分钟) xào xong rau xanh là ăn tối.",
            ),
            q_listen(
                "cau_so_sanh_nhan_manh",
                "女：这家水果店的苹果真甜，你买了几斤？\n男：我买了四斤苹果，还买了一个大西瓜。\n问：男的觉得苹果怎么样？",
                "男的觉得苹果怎么样？",
                ["很甜 [hěn tián]", "太酸了 [tài suān le]", "很贵 [hěn guì]"],
                "Táo của cửa hàng hoa quả này có vị thế nào?\nRất ngọt / Chua quá / Rất đắt",
                "Nghe tính từ miêu tả hương vị quả táo ở lượt lời đầu tiên.",
                "Câu thoại khen: 这家水果店的苹果真甜 (táo thật ngọt).",
                "Táo ở tiệm rất ngọt (很甜 / 真甜).",
            ),
        ],
    },
    3: {
        "land_name": "Học tập, sức khỏe và du lịch",
        "lesson4_name": "Công việc, nhà cửa và kế hoạch",
        "lesson4_items": [
            q_listen(
                "vi_tri_phuong_huong",
                "女：听说你上周末搬家了？新房子离公司远不远？\n男：比以前近多了，就在地铁三号线旁边，坐两站地铁就到公司。\n问：男的新家怎么样？",
                "男的新家怎么样？",
                ["离地铁站和公司很近", "离公司比以前更远", "周围没有地铁站"],
                "Nhà mới của người nam như thế nào?\nRất gần ga tàu điện ngầm và công ty / Xa công ty hơn trước / Xung quanh không có tàu điện ngầm",
                "Nghe câu trả lời của người nam: 比以前近多了，就在地铁三号线旁边.",
                "Nhà mới gần hơn trước nhiều, đi 2 trạm tàu điện ngầm là tới công ty.",
                "Nhà mới nằm ngay cạnh tuyến tàu điện ngầm số 3 và rất gần công ty.",
            ),
            q_listen(
                "thoi_gian_lich_hen",
                "男：小王，发给客户的电子合同你检查过了吗？\n女：检查过了，数字都没错，不过经理让我再补充一段售后服务说明，改好我就发出去。\n问：女的接下来要先做什么？",
                "女的接下来要先做什么？",
                ["补充售后服务说明", "去见那位客户", "重新计算合同数字"],
                "Tiếp theo người nữ phải làm việc gì trước?\nBổ sung phần thuyết minh dịch vụ hậu mãi / Đi gặp khách hàng / Tính lại con số hợp đồng",
                "Chú ý thông tin chuyển ý sau chữ 不过经理让我再…",
                "Giám đốc yêu cầu bổ sung thêm một đoạn 售后服务说明 rồi mới gửi đi.",
                "Trước khi gửi hợp đồng đi, người nữ cần bổ sung đoạn mô tả dịch vụ hậu mãi.",
            ),
            q_listen(
                "bo_ngu",
                "女：我把钥匙放进哪个包里了？怎么找不到了？\n男：别找了，刚才你换鞋的时候，顺手把它放在门口鞋柜上了。\n问：钥匙现在在哪儿？",
                "钥匙现在在哪儿？",
                ["门口的鞋柜上", "女的手提包里", "卧室的桌子上"],
                "Chìa khóa hiện đang ở đâu?\nTrên tủ giày ngoài cửa / Trong túi xách của người nữ / Trên bàn phòng ngủ",
                "Nghe người nam nhắc lại hành động lúc thay giày (换鞋的时候).",
                "Người nam nói: 顺手把它放在门口鞋柜上了.",
                "Chìa khóa đang nằm trên tủ giày ngay lối ra vào (门口的鞋柜上).",
            ),
            q_listen(
                "gia_dinh_nghe_nghiep",
                "男：这次去成都出差三天，顺便去看看大熊猫吧？\n女：恐怕没时间，会议从早排到晚，等夏天放年假我再带孩子专门去玩儿一趟。\n问：女的为什么这次不去看大熊猫？",
                "女的为什么这次不去看大熊猫？",
                ["会议安排得太满，没空", "她以前已经去看过很多次", "成都最近一直在下大雨"],
                "Vì sao lần này người nữ không đi xem gấu trúc?\nLịch họp kín từ sáng đến tối không có thời gian / Đã xem nhiều lần rồi / Thành Đô đang mưa to",
                "Nghe câu giải thích sau cụm 恐怕没时间…",
                "Người nữ nói: 会议从早排到晚 (lịch họp xếp kín từ sáng tới tối).",
                "Lịch họp chuyến công tác quá dày nên cô ấy không có thời gian đi xem gấu trúc.",
            ),
            q_listen(
                "chao_hoi_giao_tiep",
                "女：这家图书馆环境真安静，借书需要办借书证吗？\n男：不用单独办卡，只要带上身份证，在一楼机器上刷一下就能免费借五本书。\n问：在这家图书馆怎么借书？",
                "在这家图书馆怎么借书？",
                ["用身份证在一楼机器上刷一下", "必须交两百块办借书卡", "每次最多只能借一本书"],
                "Mượn sách ở thư viện này bằng cách nào?\nDùng căn cước quẹt ở máy tầng 1 / Phải đóng 200 tệ làm thẻ / Mỗi lần chỉ được mượn 1 cuốn",
                "Nghe kỹ phần hướng dẫn của người nam sau từ 只要…",
                "只要带上身份证，在一楼机器上刷一下就能免费借五本书.",
                "Chỉ cần mang căn cước công dân quẹt tại máy tự động ở tầng 1 là mượn được sách miễn phí.",
            ),
        ],
        "final_new_items": [
            q_listen(
                "lien_tu_quan_he",
                "男：今天怎么没骑你那辆蓝色自行车来学校？坏了吗？\n女：没坏，早上出门时看天阴沉沉的好像要下雨，我就坐地铁来了。\n问：女的今天为什么坐地铁来学校？",
                "女的今天为什么坐地铁来学校？",
                ["担心路上会下雨", "自行车轮胎坏了", "今天起床起晚了"],
                "Vì sao hôm nay người nữ đi tàu điện ngầm tới trường?\nLo trên đường trời mưa / Xe đạp bị hỏng / Dậy muộn",
                "Phủ định 没坏 trước, sau đó nghe lý do thực sự.",
                "Sáng ra cửa thấy trời âm u sắp mưa (好像要下雨) nên cô đi tàu điện ngầm.",
                "Thấy trời âm u có vẻ sắp mưa nên người nữ chọn đi tàu điện ngầm thay vì đạp xe.",
            ),
            q_listen(
                "so_dem_luong_tu",
                "女：先生，您的衬衫已经洗干净熨好了，一共四十元。\n男：辛苦了！我再把这件厚大衣留在这儿干洗，星期五来取可以吗？\n问：他们最可能在哪儿说话？",
                "他们最可能在哪儿说话？",
                ["洗衣店", "服装厂", "火车站"],
                "Họ có khả năng cao nhất đang nói chuyện ở đâu?\nTiệm giặt là / Xưởng may / Ga tàu hỏa",
                "Chú ý các từ khóa nghề nghiệp dịch vụ: 洗干净熨好 (giặt sạch là phẳng), 干洗 (giặt khô).",
                "Khách lấy áo sơ mi giặt xong và gửi thêm áo khoác giặt khô → tiệm giặt là (洗衣店).",
                "Ngữ cảnh trả đồ đã giặt ủi và gửi áo khoác giặt khô diễn ra tại tiệm giặt là.",
            ),
            q_listen(
                "cau_so_sanh_nhan_manh",
                "男：这道糖醋鱼做得真地道，是在楼下那家新饭馆买的吗？\n女：哪儿啊，是我照着手机视频学着做的，没想到第一次做就这么成功！\n问：这道糖醋鱼是谁做的？",
                "这道糖醋鱼是谁做的？",
                ["女的自己做的", "新饭馆厨师做的", "男的妈妈做的"],
                "Món cá sốt chua ngọt này do ai nấu?\nNgười nữ tự tay nấu / Đầu bếp quán mới nấu / Mẹ của người nam nấu",
                "Nghe cụm phủ định 哪儿啊 (Đâu có!) của người nữ.",
                "Người nữ tự hào nói: 是我照着手机视频学着做的.",
                "Người nữ tự học theo video trên điện thoại và nấu món cá chua ngọt này.",
            ),
            q_listen(
                "phu_dinh_nghi_van",
                "女：演出七点半开始，现在才六点一刻，我们去旁边的面馆吃碗面吧。\n男：好主意，吃完走过去正好检票进场。\n问：现在几点了？",
                "现在几点了？",
                ["六点十五分", "六点三十分", "七点十五分"],
                "Bây giờ là mấy giờ rồi?\n6 giờ 15 phút / 6 giờ 30 phút / 7 giờ 15 phút",
                "Đổi cách nói giờ 一刻 (1 khắc = 15 phút) sang số phút.",
                "六点一刻 = 6 giờ 15 phút (六点十五分).",
                "Một khắc (一刻) bằng 15 phút, nên 六点一刻 là 6 giờ 15 phút.",
            ),
            q_listen(
                "tro_tu_dong_thai",
                "男：林老师，下周的汉语文化节，我们班想表演一个中文小话剧，请您帮我们改改剧本好吗？\n女：当然可以，明天下午下课后你们把剧本拿到我办公室来吧。\n问：男的请林老师帮什么忙？",
                "男的请林老师帮什么忙？",
                ["修改话剧剧本", "借几套演出服装", "预定礼堂的座位"],
                "Người nam nhờ cô Lâm giúp việc gì?\nChỉnh sửa kịch bản kịch nói / Mượn trang phục biểu diễn / Đặt chỗ hội trường",
                "Nghe câu đề nghị trực tiếp ở cuối lời người nam: 请您帮我们…",
                "Người nam nhờ: 请您帮我们改改剧本好吗？ (sửa giúp kịch bản).",
                "Học sinh nhờ cô Lâm đọc và chỉnh sửa kịch bản vở kịch tiếng Trung (修改话剧剧本).",
            ),
        ],
    },
    4: {
        "land_name": "Công việc, lựa chọn và quan điểm",
        "lesson4_name": "Đàm phán, trải nghiệm và góc nhìn xã hội",
        "lesson4_items": [
            q_listen(
                "gia_dinh_nghe_nghiep",
                "男：这次应聘市场部主管的人不少，你为什么最后选了小周？他才工作三年。\n女：虽然他经验不如另外两位丰富，但他做的市场调查报告非常有针对性，提出的推广方案也最新颖。\n问：女的为什么录用小周？",
                "女的为什么录用小周？",
                ["调查深入且方案有新意", "工作年限比别人更长", "要求的工资待遇最低", "跟部门同事原本就认识"],
                "Vì sao người nữ tuyển dụng Tiểu Chu?\nKhảo sát sâu sắc và phương án mới mẻ / Thâm niên lâu hơn / Yêu cầu mức lương thấp nhất / Vốn quen sẵn đồng nghiệp",
                "Chú ý thông tin nằm sau liên từ nhượng bộ 虽然…，但…",
                "Người nữ đánh giá cao: 市场调查报告非常有针对性，推广方案也最新颖.",
                "Tiểu Chu được chọn nhờ báo cáo khảo sát sát thực tế và phương án quảng bá sáng tạo.",
            ),
            q_listen(
                "thoi_gian_lich_hen",
                "女：抱歉王总，原定明天上午十点的线上视频会议，因为我们这边系统升级，能不能改到下午两点半？\n男：下午两点半我正好要去机场接一位重要客户，不如改在后天上午同一时间吧。\n问：会议最后很可能改到什么时候？",
                "会议最后很可能改到什么时候？",
                ["后天上午十点", "明天下午两点半", "明天上午十点", "后天下午两点半"],
                "Cuộc họp cuối cùng nhiều khả năng đổi sang thời điểm nào?\n10 giờ sáng ngày kia / 2 rưỡi chiều mai / 10 giờ sáng mai / 2 rưỡi chiều ngày kia",
                "Kết hợp giờ gốc (上午十点) với đề xuất cuối cùng của người nam (后天上午同一时间).",
                "同一时间 nghĩa là cùng khung giờ với lịch gốc (10 giờ sáng) vào ngày kia (后天).",
                "Lịch gốc là 10h sáng, đổi sang 'cùng giờ sáng ngày kia' tức là 10 giờ sáng ngày kia (后天上午十点).",
            ),
            q_listen(
                "lien_tu_quan_he",
                "男：我看你最近每天中午都在休息室背单词，准备考研究生吗？\n女：不是，下个月公司派我去新加坡分公司交流半年，我想趁这几周把商务英语再强化一下。\n问：女的为什么要练习英语？",
                "女的为什么要练习英语？",
                ["下个月要去国外分公司交流", "准备参加研究生入学考试", "想换一份翻译公司的工作", "周末要接待外国旅游团"],
                "Vì sao người nữ lại ôn luyện tiếng Anh?\nTháng sau đi giao lưu tại chi nhánh nước ngoài / Chuẩn bị thi cao học / Muốn đổi sang công ty dịch thuật / Đón đoàn khách du lịch",
                "Sau từ phủ định 不是, người nữ nêu trực tiếp mục đích thật sự.",
                "下个月公司派我去新加坡分公司交流半年.",
                "Công ty cử cô sang chi nhánh Singapore giao lưu nửa năm vào tháng tới.",
            ),
            q_listen(
                "cau_so_sanh_nhan_manh",
                "女：这家新开的书店居然把一半面积都做成了咖啡区和手工体验区，书架反而没以前多了。\n男：现在人们习惯在网上买书，实体书店只有提供独特的空间体验，才能吸引读者走进来。\n问：男的认为实体书店应该怎么做？",
                "男的认为实体书店应该怎么做？",
                ["提供独特的线下空间体验", "完全停止卖书改开咖啡馆", "把所有图书按五折出售", "搬到房租更便宜的郊区去"],
                "Người nam cho rằng hiệu sách truyền thống nên làm gì?\nMang lại trải nghiệm không gian trực tiếp độc đáo / Ngừng bán sách hẳn / Giảm giá 50% toàn bộ sách / Chuyển ra ngoại ô",
                "Nghe câu điều kiện cần thiết của người nam: 实体书店只有…，才能…",
                "只有提供独特的空间体验，才能吸引读者走进来.",
                "Hiệu sách trực tiếp cần tạo ra trải nghiệm không gian độc đáo để thu hút độc giả.",
            ),
            q_listen(
                "bo_ngu",
                "许多人买衣服时喜欢追赶流行，结果衣柜塞得满满的，第二年却觉得哪件都过时了。其实，挑选剪裁合身、面料舒适的经典款式，不仅耐看，反而更省钱。\n问：这段话建议大家买什么样的衣服？",
                "这段话建议大家买什么样的衣服？",
                ["合身舒适的经典款式", "当季最流行的新奇款式", "商场里打折最便宜的衣服", "颜色最鲜艳夺目的衣服"],
                "Đoạn độc thoại khuyên mọi người nên mua kiểu quần áo nào?\nKiểu dáng kinh điển vừa vặn, chất liệu thoải mái / Mẫu mốt mới lạ nhất / Đồ giảm giá rẻ nhất / Đồ màu sắc sặc sỡ nhất",
                "Lắng nghe câu khuyên nằm sau từ chuyển ý 其实…",
                "挑选剪裁合身、面料舒适的经典款式，不仅耐看，反而更省钱.",
                "Chọn trang phục kiểu dáng cổ điển, vừa người và chất vải dễ chịu sẽ bền đẹp và tiết kiệm hơn.",
            ),
        ],
        "final_new_items": [
            q_listen(
                "phu_dinh_nghi_van",
                "男：奇怪，我明明把U盘放在办公桌抽屉里了，怎么不见了？\n女：你忘啦？上午去打印室印会议材料的时候，你插在打印室电脑上没拔下来，我帮你收着呢。\n问：U盘现在在谁那儿？",
                "U盘现在在谁那儿？",
                ["在女的那儿", "在打印室电脑上", "在办公桌抽屉里", "被客户借走了"],
                "Chiếc USB hiện đang ở chỗ ai?\nỞ chỗ người nữ / Cắm ở máy tính phòng in / Trong ngăn kéo bàn làm việc / Khách mượn rồi",
                "Đừng dừng ở chi tiết phòng in, hãy nghe hết câu cuối cùng của người nữ!",
                "Câu cuối người nữ nói: 我帮你收着呢 (mình đang cất giúp cậu đây).",
                "Người nữ đã rút chiếc USB ở phòng in và đang giữ giúp người nam.",
            ),
            q_listen(
                "chao_hoi_giao_tiep",
                "女：张师傅，这台空调修好以后还会不会再漏水？\n男：放心吧，刚才是因为排水管堵住了，我已经彻底清理干净，并且给您换了一个新接口，保修一年。\n问：空调刚才出了什么问题？",
                "空调刚才出了什么问题？",
                ["排水管堵住导致漏水", "遥控器没有电池了", "压缩机完全烧坏了", "室内温度调得太高"],
                "Chiếc điều hòa vừa rồi gặp trục trặc gì?\nỐng thoát nước bị tắc gây rò nước / Điều khiển hết pin / Hỏng máy nén / Chỉnh nhiệt độ quá cao",
                "Nghe kỹ nguyên nhân thợ sửa giải thích sau chữ 刚才是因为…",
                "刚才是因为排水管堵住了 (ống thoát nước bị nghẹt).",
                "Điều hòa bị rò nước do đường ống thoát nước bị tắc nghẽn.",
            ),
            q_listen(
                "vi_tri_phuong_huong",
                "男：听说市美术馆这周末有敦煌壁画展，我们要不要现场去买票？\n女：这个展览特别火，现场根本买不到票，必须提前三天在公众号上实名预约，我昨晚已经帮咱们俩约好了。\n问：关于这次展览，下列哪项正确？",
                "关于这次展览，下列哪项正确？",
                ["女的已经提前预约好了门票", "只能周末去现场排队买票", "展览改到下个月才正式开始", "参观展览不需要实名预约"],
                "Điều nào sau đây đúng về buổi triển lãm lần này?\nNgười nữ đã đặt lịch vé trước cho hai người / Chỉ bán vé tại quầy / Dời sang tháng sau / Không cần đặt trước",
                "Nghe thông tin ở câu cuối của người nữ.",
                "Người nữ nói: 我昨晚已经帮咱们俩约好了.",
                "Triển lãm phải đặt lịch trước trên mạng và người nữ đã đặt xong cho cả hai từ tối qua.",
            ),
            q_listen(
                "so_dem_luong_tu",
                "科学研究表明，午饭后小睡二十到三十分钟，能有效缓解上午大脑的疲劳，使下午的工作效率提高百分之三十以上；但如果睡超过一个小时，醒来后反而容易觉得困倦。\n问：午睡多长时间比较合适？",
                "午睡多长时间比较合适？",
                ["二十到三十分钟", "一个半小时左右", "越长对大脑越好", "五分钟以内最好"],
                "Ngủ trưa khoảng bao lâu là hợp lý?\n20 đến 30 phút / Khoảng 1 tiếng rưỡi / Càng lâu càng tốt / Dưới 5 phút",
                "Chú ý con số thời gian đầu đoạn và cảnh báo sau chữ 但如果…",
                "午饭后小睡二十到三十分钟 giúp phục hồi sự tỉnh táo hiệu quả nhất.",
                "Ngủ trưa ngắn từ 20–30 phút giúp tăng hiệu suất buổi chiều mà không gây mệt mỏi khi thức dậy.",
            ),
            q_listen(
                "lien_tu_quan_he",
                "年轻人在学一门新技能时，最容易犯的毛病就是花太多时间挑选教材和工具，却迟迟不肯动手开始练。其实，先用现有的条件迈出第一步，在练习中慢慢调整，才是最快的成长路径。\n问：这段话主要鼓励年轻人怎么做？",
                "这段话主要鼓励年轻人怎么做？",
                ["尽早动手开始行动与练习", "花几个月挑最好的工具", "等条件完美无缺再开始", "同时报名十几个培训班"],
                "Đoạn văn chủ yếu khích lệ người trẻ làm gì?\nBắt tay vào hành động và luyện tập càng sớm càng tốt / Dành vài tháng chọn công cụ / Đợi đủ điều kiện hoàn hảo / Đăng ký chục lớp học cùng lúc",
                "Nghe câu thông điệp chính mở đầu bằng 其实…",
                "先用现有的条件迈出第一步，在练习中慢慢调整.",
                "Thông điệp cốt lõi là hãy bắt tay hành động ngay từ bước đầu tiên thay vì chần chừ chuẩn bị quá lâu.",
            ),
        ],
    },
}


def main() -> int:
    db = SessionLocal()
    try:
        uid = db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one()
        levels = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}
        nhom_map = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM nhom_kien_thuc")).all()}

        # Thu thập danh sách câu cần tạo âm thanh cho các thửa còn thiếu vị trí 4 hoặc 5
        tasks = []
        for cap, cfg in SUPPLEMENTS.items():
            level_id = levels[f"HSK{cap}"]
            land = db.execute(
                text("""
                    SELECT id, ma_goc_id FROM bo_de
                    WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'nghe' AND ten = :t
                    ORDER BY phien_ban DESC LIMIT 1
                """),
                {"c": level_id, "t": cfg["land_name"]},
            ).mappings().first()
            if not land:
                print(f"✗ Không tìm thấy thửa Nghe HSK {cap} · {cfg['land_name']}")
                continue
            slots = {
                int(x) for x in db.execute(
                    text("SELECT vi_tri FROM bo_de WHERE thua_id = :g AND loai IN ('bai', 'cuoi_thua')"),
                    {"g": land["ma_goc_id"]},
                ).scalars().all()
            }
            if 4 in slots and 5 in slots:
                print(f"· Bỏ qua Nghe HSK {cap} · {cfg['land_name']} (đã đủ 5 vị trí)")
                continue
            tasks.append((cap, level_id, dict(land), slots, cfg))

        if not tasks:
            print("Mọi thửa Nghe HSK 2–4 đã đủ 5 vị trí.")
            return 0

        # Tạo âm thanh song song bằng giọng đọc đa nhân vật (男 / 女 / 问)
        audio_jobs = []
        for cap, _, _, slots, cfg in tasks:
            if 4 not in slots:
                for item in cfg["lesson4_items"]:
                    audio_jobs.append((cap, item))
            if 5 not in slots:
                for item in cfg["final_new_items"]:
                    audio_jobs.append((cap, item))

        print(f"Đang tổng hợp {len(audio_jobs)} tệp âm thanh đối thoại đa giọng cho Nghe HSK 2–4...")

        def synth(job):
            cap, item = job
            plays = 2 if cap <= 3 else 1
            slow = cap <= 2
            item["tep_audio"] = make_audio(item["loi_nghe"], plays=plays, slow=slow)
            return item["tep_audio"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(synth, audio_jobs))

        slot_counter = 0
        for cap, level_id, land, slots, cfg in tasks:
            existing_qids = [
                int(x) for x in db.execute(
                    text("""
                        SELECT i.cau_hoi_id
                        FROM bo_de b JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id
                        WHERE b.thua_id = :g AND b.trang_thai = 'da_dang'
                        ORDER BY b.vi_tri, i.thu_tu
                    """),
                    {"g": land["ma_goc_id"]},
                ).scalars().all()
            ]

            def save_item(spec: dict) -> int:
                nonlocal slot_counter
                opts, ans = place(spec["raw_opts"], 0, slot_counter)
                slot_counter += 1
                qid = create_question(db, QuestionIn(
                    dang="chon_mot",
                    cap_do_id=level_id,
                    ky_nang="nghe",
                    dung_on_luyen=True,
                    dung_thi_thu=False,
                    nguon_noi_dung="tu_soan",
                    nhom_kien_thuc_id=nhom_map.get(spec["nhom"]),
                    tep_audio=spec["tep_audio"],
                    noi_dung=spec["noi_dung"],
                    loi_nghe=spec["loi_nghe"],
                    dich_nghia=spec["dich_nghia"],
                    goi_y=spec["goi_y"],
                    goi_y_2=spec["goi_y_2"],
                    giai_thich=spec["giai_thich"],
                    phuong_an=mc(opts, ans),
                ), uid)
                publish_question(db, qid, uid)
                return qid

            if 4 not in slots:
                l4_qids = [save_item(it) for it in cfg["lesson4_items"]]
                l4_id = path_service.create_lesson(
                    db,
                    SimpleNamespace(thua_id=land["id"], vi_tri=4, ten=cfg["lesson4_name"], muc_tieu=None, tai_lieu_id=None),
                    uid,
                )
                path_service.set_lesson_items(db, l4_id, [SimpleNamespace(cau_hoi_id=q) for q in l4_qids])
                path_service.lesson_status(db, l4_id, "dang")
                print(f"→ Đã đăng Nghe HSK {cap} · Bài 4: {cfg['lesson4_name']} (5 câu)")

            if 5 not in slots:
                f_new_qids = [save_item(it) for it in cfg["final_new_items"]]
                # Kết hợp 5 câu tiêu biểu từ Bài 1–3 + 5 câu mới tinh cho Kiểm tra cuối thửa (10 câu không trùng)
                review_picks = [existing_qids[idx] for idx in (0, 3, 6, 9, 12) if idx < len(existing_qids)]
                final_10 = f_new_qids + review_picks[: 10 - len(f_new_qids)]
                l5_id = path_service.create_lesson(
                    db,
                    SimpleNamespace(thua_id=land["id"], vi_tri=5, ten="Kiểm tra cuối thửa", muc_tieu=None, tai_lieu_id=None),
                    uid,
                )
                path_service.set_lesson_items(db, l5_id, [SimpleNamespace(cau_hoi_id=q) for q in final_10])
                path_service.lesson_status(db, l5_id, "dang")
                print(f"→ Đã đăng Nghe HSK {cap} · Vị trí 5: Kiểm tra cuối thửa ({len(final_10)} câu)")

        print("HOÀN TẤT BỔ SUNG NGHE HSK 2–4!")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
