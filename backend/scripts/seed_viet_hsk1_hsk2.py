"""Nạp bổ sung lộ trình kỹ năng Viết cơ bản (Ghép câu & Điền chữ) cho HSK 1 và HSK 2.

- Đảm bảo mọi cấp độ HSK 1–4 đều có đầy đủ cả 4 kỹ năng (Từ vựng, Nghe, Đọc, Viết).
- Mỗi cấp (HSK 1, HSK 2) gồm 20 câu chuẩn (`sap_xep` và `dien_chu`), chia thành 2 Thửa × (4 Bài thường + 1 Bài kiểm tra cuối thửa),
  đủ nguồn câu (>= 15 câu/cấp) cho cả bài kiểm tra Bắt đầu cấp (10 câu) và Vượt chặng (15 câu).
- Chạy an toàn nhiều lần (idempotent): không tạo trùng nếu đã tồn tại.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.root_id import next_root_id
from app.database.session import SessionLocal

# Cấu trúc câu sap_xep: (nhom_ma, nghia_vi, pieces, accepted_list, goi_y_1, goi_y_2, giai_thich)
# Cấu trúc câu dien_chu: (nhom_ma, noi_dung, pinyin, nghia_vi, accepted_list, goi_y_1, goi_y_2, giai_thich)

HSK1_LANDS = [
    {
        "vi_tri": 1,
        "ten": "Ghép câu chào hỏi & gia đình",
        "muc_tieu": "Nắm vững trật tự Chủ ngữ + Động từ + Tân ngữ trong câu giao tiếp HSK 1",
        "lessons": [
            (
                "Chào hỏi và giới thiệu tên",
                "Ghép câu tự giới thiệu tên, quốc tịch và hỏi thăm sức khỏe",
                [
                    ("sap_xep", "chao_hoi_giao_tiep", "Tôi tên là Lý Nguyệt.", ["我", "叫", "李月"], ["我叫李月"],
                     "Tìm đại từ nhân xưng chỉ 'tôi' đứng đầu câu.", "Cấu trúc tự giới thiệu tên: Chủ ngữ + 叫 + Tên riêng.",
                     "我叫李月 (Wǒ jiào Lǐ Yuè): Tôi tên là Lý Nguyệt."),
                    ("sap_xep", "chao_hoi_giao_tiep", "Bạn là người nước nào?", ["你", "是", "哪国", "人"], ["你是哪国人"],
                     "Đặt chủ ngữ 你 lên đầu câu.", "Cụm từ hỏi quốc tịch là 哪国人 đứng sau động từ 是.",
                     "你是哪国人 (Nǐ shì nǎ guó rén): Bạn là người nước nào?"),
                    ("sap_xep", "chao_hoi_giao_tiep", "Rất vui được quen biết bạn.", ["很", "高兴", "认识", "你"], ["很高兴认识你"],
                     "Mở đầu bằng phó từ chỉ mức độ 很 + tính từ cảm xúc.", "Cụm 很高兴 đi trước động từ 认识 + tân ngữ 你.",
                     "很高兴认识你 (Hěn gāoxìng rènshi nǐ): Rất vui được quen biết bạn."),
                    ("dien_chu", "chao_hoi_giao_tiep", "对不起，没___系。", "duìbuqǐ , méi ___ xì .", "Xin lỗi, không sao đâu.",
                     ["关"], "Từ ghép gồm 2 chữ mang nghĩa 'không sao': 没__系.", "Điền chữ 关 (guān) trong cụm 没关系.",
                     "没关系 (méi guānxi) là lời đáp lịch sự cho 对不起."),
                    ("dien_chu", "phu_dinh_nghi_van", "她___是我的老师，她是医生。", "tā ___ shì wǒ de lǎoshī , tā shì yīshēng .",
                     "Cô ấy không phải giáo viên của tôi, cô ấy là bác sĩ.",
                     ["不"], "Trước động từ 是 dùng phó từ phủ định nào?", "Điền chữ 不 (bù) để tạo cụm 不是 (không phải).",
                     " phủ định cho động từ 是 luôn dùng 不 (不是)."),
                ],
            ),
            (
                "Gia đình và nghề nghiệp",
                "Sắp xếp câu giới thiệu thành viên gia đình và nơi làm việc",
                [
                    ("sap_xep", "gia_dinh_nghe_nghiep", "Nhà tôi có bốn người.", ["我家", "有", "四", "口", "人"], ["我家有四口人"],
                     "Chủ ngữ chỉ gia đình đứng đầu câu.", "Số lượng thành viên gia đình dùng Số từ + 口 + 人 sau động từ 有.",
                     "我家有四口人: Nhà tôi có 4 nhân khẩu."),
                    ("sap_xep", "gia_dinh_nghe_nghiep", "Mẹ tôi làm việc ở trường học.", ["我妈妈", "在", "学校", "工作"], ["我妈妈在学校工作"],
                     "Trong tiếng Trung, nơi chốn đặt trước động từ chính.", "Cấu trúc: Chủ ngữ + 在 + Địa điểm + Động từ (工作).",
                     "我妈妈在学校工作: Mẹ tôi làm việc ở trường học."),
                    ("sap_xep", "gia_dinh_nghe_nghiep", "Anh ấy là bạn học Trung Quốc của tôi.", ["他", "是", "我的", "中国", "同学"], ["他是我的中国同学"],
                     "Định ngữ sở hữu 我的 đứng trước danh từ chính.", "Trật tự cụm danh từ: 我的 + 中国 + 同学.",
                     "他是我的中国同学: Anh ấy là bạn học người Trung Quốc của tôi."),
                    ("dien_chu", "gia_dinh_nghe_nghiep", "你女儿今年几___了？", "nǐ nǚ'ér jīnnián jǐ ___ le ?",
                     "Con gái bạn năm nay mấy tuổi rồi?",
                     ["岁"], "Từ dùng để hỏi tuổi cho trẻ nhỏ đi sau 几.", "Điền chữ 岁 (suì = tuổi).",
                     "几岁 dùng để hỏi tuổi (thường cho trẻ em dưới 10 tuổi)."),
                    ("sap_xep", "phu_dinh_nghi_van", "Người kia là ai vậy?", ["那个人", "是", "谁"], ["那个人是谁"],
                     "Chủ ngữ 那个人 đứng đầu câu.", "Đại từ nghi vấn 谁 đứng sau động từ 是.",
                     "那个人是谁 (Nàge rén shì shéi): Người kia là ai?"),
                ],
            ),
            (
                "Học tiếng Hán và đọc sách",
                "Viết câu với động từ năng nguyện 想, 会 và câu hỏi 怎么",
                [
                    ("sap_xep", "chao_hoi_giao_tiep", "Tôi biết nói tiếng Hán.", ["我", "会", "说", "汉语"], ["我会说汉语"],
                     "Động từ năng nguyện chỉ kỹ năng học được đứng trước động từ thường.", "Cấu trúc: 我 + 会 + 说 + 汉语.",
                     "会 biểu thị kỹ năng thông qua học tập mà biết (我会说汉语)."),
                    ("sap_xep", "phu_dinh_nghi_van", "Chữ Hán này viết như thế nào?", ["这个", "汉字", "怎么", "写"], ["这个汉字怎么写"],
                     "Đưa đối tượng 这个汉字 lên làm chủ ngữ.", "Từ hỏi cách thức 怎么 đứng ngay trước động từ 写.",
                     "这个汉字怎么写: Chữ Hán này viết thế nào?"),
                    ("sap_xep", "so_dem_luong_tu", "Thầy giáo có nhiều sách tiếng Hán.", ["老师", "有", "很多", "汉语书"], ["老师有很多汉语书"],
                     "Chủ ngữ 老师 đứng đầu, theo sau là động từ sở hữu 有.", "Cụm số lượng 很多 bổ nghĩa cho 汉语书.",
                     "老师有很多汉语书: Thầy giáo có rất nhiều sách tiếng Hán."),
                    ("dien_chu", "chao_hoi_giao_tiep", "你会___汉字吗？", "nǐ huì ___ hànzì ma ?",
                     "Bạn có biết viết chữ Hán không?",
                     ["写"], "Động từ mang nghĩa 'viết' đi với tân ngữ 汉字.", "Điền chữ 写 (xiě = viết).",
                     "写汉字 (xiě hànzì): viết chữ Hán."),
                    ("sap_xep", "phu_dinh_nghi_van", "Hôm qua anh ấy không đến trường.", ["昨天", "他", "没", "去", "学校"], ["昨天他没去学校", "他昨天没去学校"],
                     "Hành động quá khứ chưa xảy ra dùng phó từ phủ định 没.", "Trật tự: Thời gian/Chủ ngữ + 没 + 去 + 学校.",
                     "Phủ định hành động trong quá khứ dùng 没 (没去学校)."),
                ],
            ),
            (
                "Ôn ghép câu giao tiếp tổng hợp",
                "Kết hợp câu hỏi gì, ở đâu và câu trần thuật cơ bản",
                [
                    ("sap_xep", "phu_dinh_nghi_van", "Bạn muốn ăn món gì?", ["你", "想", "吃", "什么"], ["你想吃什么"],
                     "Đặt đại từ nghi vấn 什么 ở vị trí tân ngữ cuối câu.", "Cấu trúc: 你 + 想 + 吃 + 什么.",
                     "你想吃什么: Bạn muốn ăn gì?"),
                    ("sap_xep", "chao_hoi_giao_tiep", "Bạn học của tôi rất thích xem phim.", ["我同学", "很", "喜欢", "看电影"], ["我同学很喜欢看电影"],
                     "Phó từ mức độ 很 đứng trước tâm lý động từ 喜欢.", "Cấu trúc: 我同学 + 很喜欢 + 看电影.",
                     "我同学很喜欢看电影: Bạn học tôi rất thích xem phim."),
                    ("dien_chu", "chao_hoi_giao_tiep", "请___，喝杯热茶吧。", "qǐng ___ , hē bēi rè chá ba .",
                     "Mời ngồi, uống tách trà nóng nhé.",
                     ["坐"], "Động từ lịch sự mời khách ngồi xuống sau chữ 请.", "Điền chữ 坐 (zuò = ngồi).",
                     "请坐 (qǐng zuò): mời ngồi."),
                    ("sap_xep", "gia_dinh_nghe_nghiep", "Con trai ông ấy làm việc tại Bắc Kinh.", ["他儿子", "在", "北京", "工作"], ["他儿子在北京工作"],
                     "Chủ ngữ 他儿子 đứng trước cụm giới từ chỉ nơi chốn.", "Cấu trúc: 他儿子 + 在北京 + 工作.",
                     "他儿子在北京工作: Con trai ông ấy làm việc ở Bắc Kinh."),
                    ("dien_chu", "chao_hoi_giao_tiep", "不客___，再见！", "bú kè ___ , zàijiàn !",
                     "Đừng khách sáo, tạm biệt!",
                     ["气"], "Cụm từ đáp lại lời cảm ơn 谢谢 là 不客__.", "Điền chữ 气 (qi) tạo thành 不客气.",
                     "不客气 (bú kèqi): không có chi / đừng khách sáo."),
                ],
            ),
        ],
    },
    {
        "vi_tri": 2,
        "ten": "Thời gian, vị trí & mua sắm",
        "muc_tieu": "Viết đúng trạng ngữ thời gian, từ chỉ vị trí và lượng từ HSK 1",
        "lessons": [
            (
                "Giờ giấc và lịch trình trong ngày",
                "Đặt đúng thứ tự Năm – Tháng – Ngày – Buổi – Giờ trong câu tiếng Trung",
                [
                    ("sap_xep", "thoi_gian_lich_hen", "Bây giờ là chín giờ rưỡi sáng.", ["现在", "上午", "九点", "半"], ["现在上午九点半"],
                     "Tiếng Trung sắp xếp thời gian từ đơn vị lớn đến đơn vị nhỏ.", "现在 -> 上午 (buổi) -> 九点半 (giờ).",
                     "现在上午九点半: Bây giờ là 9 giờ 30 sáng."),
                    ("sap_xep", "thoi_gian_lich_hen", "Hôm nay là thứ sáu ngày mười tháng tám.", ["今天", "八月", "十号", "星期五"], ["今天八月十号星期五"],
                     "Tháng đứng trước ngày, thứ đứng sau ngày.", "今天 + 八月 + 十号 + 星期五.",
                     "Thứ tự ngày tháng chuẩn: Tháng (月) -> Ngày (号) -> Thứ (星期)."),
                    ("sap_xep", "thoi_gian_lich_hen", "Khi nào chúng ta đi ăn cơm?", ["我们", "什么时候", "去", "吃饭"], ["我们什么时候去吃饭", "什么时候我们去吃饭"],
                     "Cụm hỏi thời điểm 什么时候 đặt trước động từ 去.", "Cấu trúc: 我们 + 什么时候 + 去吃饭.",
                     "什么时候 dùng để hỏi thời gian, luôn đứng trước động từ."),
                    ("dien_chu", "thoi_gian_lich_hen", "明天下___三点见。", "míngtiān xià ___ sān diǎn jiàn .",
                     "Ba giờ chiều mai gặp nhé.",
                     ["午"], "Từ chỉ 'buổi chiều' ghép bởi chữ 下 và chữ gì?", "Điền chữ 午 (wǔ) tạo thành 下午.",
                     "下午 (xiàwǔ): buổi chiều."),
                    ("sap_xep", "thoi_gian_lich_hen", "Thứ bảy tuần này tôi về nhà.", ["这个", "星期六", "我", "回家"], ["这个星期六我回家", "我这个星期六回家"],
                     "Cụm thời gian 这个星期六 đứng đầu câu hoặc ngay sau chủ ngữ 我.", "Động từ ly hợp 回家 đứng cuối câu.",
                     "这个星期六我回家: Thứ bảy này tôi về nhà."),
                ],
            ),
            (
                "Vị trí và phương hướng",
                "Dùng chuẩn động từ 在, 有 với phương vị từ 上, 下, 里, 前, 后",
                [
                    ("sap_xep", "vi_tri_phuong_huong", "Trên cái bàn có một chiếc cốc.", ["桌子上", "有", "一个", "杯子"], ["桌子上有一个杯子"],
                     "Câu tồn hiện mở đầu bằng từ chỉ vị trí 桌子上.", "Vị trí + 有 + Số lượng (一个) + Danh từ (杯子).",
                     "桌子上有一个杯子: Trên bàn có một cái cốc."),
                    ("sap_xep", "vi_tri_phuong_huong", "Trường học ở phía trước cửa hàng.", ["学校", "在", "商店", "前面"], ["学校在商店前面"],
                     "Chủ ngữ 学校 + 在 + Danh từ mốc + Phương vị từ.", "商店前面 nghĩa là phía trước cửa hàng.",
                     "学校在商店前面: Trường học nằm ở phía trước cửa hàng."),
                    ("sap_xep", "vi_tri_phuong_huong", "Chú chó nhỏ đang ở dưới ghế.", ["小狗", "在", "椅子", "下面"], ["小狗在椅子下面"],
                     "Phương vị từ 下面 đặt sau danh từ 椅子.", "Cấu trúc: 小狗 + 在 + 椅子下面.",
                     "椅子下面: ở phía dưới cái ghế."),
                    ("dien_chu", "vi_tri_phuong_huong", "你爸爸___家吗？", "nǐ bàba ___ jiā ma ?",
                     "Bố của bạn có ở nhà không?",
                     ["在"], "Động từ chỉ sự có mặt tại một địa điểm.", "Điền chữ 在 (zài = ở).",
                     "在家 (zài jiā): có ở nhà."),
                    ("sap_xep", "vi_tri_phuong_huong", "Phía sau bệnh viện là nhà tôi.", ["医院", "后面", "是", "我家"], ["医院后面是我家"],
                     "Cụm phương vị 医院后面 làm chủ ngữ đứng đầu câu.", "医院后面 + 是 + 我家.",
                     "医院后面是我家: Phía sau bệnh viện là nhà của tôi."),
                ],
            ),
            (
                "Số đếm, lượng từ và mua sắm",
                "Ghép lượng từ 个, 本, 件, 块 và câu hỏi giá tiền 多少钱",
                [
                    ("sap_xep", "so_dem_luong_tu", "Bộ quần áo này giá bao nhiêu tiền?", ["这件", "衣服", "多少", "钱"], ["这件衣服多少钱"],
                     "Lượng từ 件 đi liền với 这 trước danh từ 衣服.", "Cụm hỏi giá 多少钱 đặt cuối câu.",
                     "这件衣服多少钱: Bộ quần áo này bao nhiêu tiền?"),
                    ("sap_xep", "so_dem_luong_tu", "Tôi mua năm quả táo đỏ.", ["我", "买", "五", "个", "苹果"], ["我买五个苹果"],
                     "Số từ 五 + lượng từ 个 đứng trước danh từ 苹果.", "Cấu trúc: 我 + 买 + 五个 + 苹果.",
                     "五个苹果: năm quả táo."),
                    ("dien_chu", "so_dem_luong_tu", "我想要一___水。", "wǒ xiǎng yào yì ___ shuǐ .",
                     "Tôi muốn lấy một cốc nước.",
                     ["杯"], "Lượng từ chỉ 'cốc / ly' cho đồ uống.", "Điền chữ 杯 (bēi = cốc, ly).",
                     "一杯水 (yì bēi shuǐ): một cốc nước."),
                    ("sap_xep", "so_dem_luong_tu", "Quyển sách này ba mươi đồng.", ["这本", "书", "三十", "块", "钱"], ["这本书三十块钱"],
                     "Chủ ngữ 这本书 đứng đầu, cụm giá tiền đứng sau làm vị ngữ.", "三十 + 块 + 钱 = 30 đồng.",
                     "这本书三十块钱: Quyển sách này giá 30 tệ."),
                    ("dien_chu", "so_dem_luong_tu", "房间里有六___椅子。", "fángjiān lǐ yǒu liù ___ yǐzi .",
                     "Trong phòng có sáu chiếc ghế.",
                     ["把", "个"], "Lượng từ thông dụng đi với ghế 椅子.", "Điền chữ 把 (hoặc 个).",
                     "椅子 thường đi với lượng từ 把 (hoặc 个 trong khẩu ngữ cơ bản)."),
                ],
            ),
            (
                "Đi lại và thời tiết HSK 1",
                "Viết câu về phương tiện đi lại và mô tả thời tiết hôm nay",
                [
                    ("sap_xep", "vi_tri_phuong_huong", "Chúng tôi gọi taxi ra sân bay.", ["我们", "坐", "出租车", "去", "机场"], ["我们坐出租车去机场"],
                     "Câu liên động: phương thức đi lại đứng trước động từ chỉ hướng.", "坐出租车 (đi bằng taxi) đặt trước 去机场 (ra sân bay).",
                     "我们坐出租车去机场: Chúng tôi đi taxi đến sân bay."),
                    ("sap_xep", "thoi_gian_lich_hen", "Thời tiết hôm nay thật là nóng.", ["今天", "的", "天气", "太", "热了"], ["今天的天气太热了"],
                     "Cụm chủ ngữ 今天的天气 đứng đầu câu.", "Cấu trúc cảm thán 太 + Tính từ + 了 (太热了).",
                     "今天的天气太热了: Thời tiết hôm nay nóng quá."),
                    ("dien_chu", "thoi_gian_lich_hen", "今天下___，我不去商店。", "jīntiān xià ___ , wǒ bú qù shāngdiàn .",
                     "Hôm nay trời mưa, tôi không đi cửa hàng.",
                     ["雨"], "Từ chỉ 'trời mưa' ghép bởi 下 và danh từ chỉ mưa.", "Điền chữ 雨 (yǔ = mưa).",
                     "下雨 (xià yǔ): trời mưa."),
                    ("sap_xep", "thoi_gian_lich_hen", "Khi nào anh ấy quay về Bắc Kinh?", ["他", "什么时候", "回", "北京"], ["他什么时候回北京", "什么时候他回北京"],
                     "Động từ 回 (quay về) mang tân ngữ địa điểm 北京.", "Cấu trúc: 他 + 什么时候 + 回 + 北京.",
                     "他什么时候回北京: Khi nào anh ấy về Bắc Kinh?"),
                    ("sap_xep", "chao_hoi_giao_tiep", "Tôi gọi điện thoại cho bạn học.", ["我", "给", "同学", "打电话"], ["我给同学打电话"],
                     "Giới từ 给 + người nhận đứng trước cụm động từ 打电话.", "Cấu trúc: 我 + 给同学 + 打电话.",
                     "给 A 打电话: gọi điện thoại cho A."),
                ],
            ),
        ],
    },
]

HSK2_LANDS = [
    {
        "vi_tri": 1,
        "ten": "Khoảng cách, thời lượng & bổ ngữ kết quả",
        "muc_tieu": "Sử dụng thành thạo cấu trúc 从…到…, 离 và bổ ngữ kết quả 完 / 懂 / 到",
        "lessons": [
            (
                "Khoảng cách với 离 và 从…到…",
                "Phân biệt vị trí của 离 và cặp giới từ 从…到… trong câu viết HSK 2",
                [
                    ("sap_xep", "vi_tri_phuong_huong", "Nhà tôi cách trường học không xa.", ["我家", "离", "学校", "不远"], ["我家离学校不远"],
                     "Cấu trúc khoảng cách: Địa điểm A + 离 + Địa điểm B + Tính từ.", "我家 + 离 + 学校 + 不远.",
                     "A 离 B + 远/近 biểu thị khoảng cách giữa hai nơi."),
                    ("sap_xep", "thoi_gian_lich_hen", "Từ tám giờ đến mười hai giờ tôi đều bận.", ["从", "八点", "到", "十二点", "我都很忙"], ["从八点到十二点我都很忙", "我从八点到十二点都很忙"],
                     "Cặp mốc thời gian mở đầu bằng 从 và nối bằng 到.", "从八点到十二点 + 我都很忙.",
                     "从 A 到 B diễn tả khoảng thời gian từ A đến B."),
                    ("sap_xep", "vi_tri_phuong_huong", "Đi xe buýt đến công ty mất hai mươi phút.", ["坐", "公共汽车", "到公司", "要", "二十分钟"], ["坐公共汽车到公司要二十分钟"],
                     "Phương tiện 坐公共汽车 đứng trước đích đến 到公司.", "Động từ 要 đứng trước khoảng thời gian 二十分钟.",
                     "坐公共汽车到公司要二十分钟: Đi xe buýt tới công ty mất 20 phút."),
                    ("dien_chu", "vi_tri_phuong_huong", "机场___这儿有一点儿远。", "jīchǎng ___ zhèr yǒuyìdiǎnr yuǎn .",
                     "Sân bay cách đây hơi xa một chút.",
                     ["离"], "Giới từ chỉ khoảng cách giữa 机场 và 这儿.", "Điền chữ 离 (lí = cách).",
                     "机场离这儿…: Sân bay cách nơi này…"),
                    ("sap_xep", "thoi_gian_lich_hen", "Mỗi ngày anh ấy bơi một tiếng đồng hồ.", ["他", "每天", "游泳", "一个", "小时"], ["他每天游泳一个小时", "每天他游泳一个小时"],
                     "Bổ ngữ thời lượng 一个小时 đặt ngay sau động từ 游泳.", "他 + 每天 + 游泳 + 一个小时.",
                     "Thời lượng thực hiện hành động đứng sau động từ."),
                ],
            ),
            (
                "Bổ ngữ kết quả 完, 懂, 到, 见",
                "Ghép đúng động từ với bổ ngữ kết quả và phủ định bằng 没",
                [
                    ("sap_xep", "bo_ngu", "Quyển sách này tôi đã đọc xong rồi.", ["这本书", "我", "看完", "了"], ["这本书我看完了", "我看完了这本书"],
                     "Đưa tân ngữ xác định 这本书 lên đầu câu làm chủ đề.", "Động từ 看 ghép bổ ngữ kết quả 完 + 了.",
                     "看完 biểu thị hành động đọc đã hoàn tất."),
                    ("sap_xep", "bo_ngu", "Tôi không nghe hiểu câu anh ấy nói.", ["我", "没", "听懂", "他说的", "话"], ["我没听懂他说的话"],
                     "Phủ định bổ ngữ kết quả dùng 没 trước động từ.", "我 + 没听懂 + 他说的话.",
                     "没听懂: đã nghe nhưng chưa hiểu được nội dung."),
                    ("sap_xep", "bo_ngu", "Bạn đã tìm thấy điện thoại chưa?", ["你", "找到", "手机", "了", "吗"], ["你找到手机了吗"],
                     "Bổ ngữ kết quả 到 đi ngay sau động từ 找.", "你 + 找到 + 手机 + 了吗.",
                     "找到 (zhǎodào): tìm thấy."),
                    ("dien_chu", "bo_ngu", "今天的考试题我做___了。", "jīntiān de kǎoshì tí wǒ zuò ___ le .",
                     "Đề thi hôm nay tôi đã làm xong hết rồi.",
                     ["完"], "Bổ ngữ kết quả chỉ sự hoàn thành đi sau động từ 做.", "Điền chữ 完 (wán = xong).",
                     "做完 (zuò wán): làm xong."),
                    ("sap_xep", "bo_ngu", "Tôi nhìn thấy thầy giáo ở ngoài cửa.", ["我", "在门外", "看见", "老师", "了"], ["我在门外看见老师了"],
                     "Trạng ngữ nơi chốn 在门外 đứng trước động từ 看见.", "我 + 在门外 + 看见 + 老师了.",
                     "看见 (kànjiàn): nhìn thấy."),
                ],
            ),
            (
                "Bổ ngữ trạng thái với 得",
                "Viết câu nhận xét mức độ nhanh, sớm, giỏi với trợ từ kết cấu 得",
                [
                    ("sap_xep", "bo_ngu", "Cô ấy hát rất hay.", ["她", "唱", "得", "非常", "好听"], ["她唱得非常好听"],
                     "Trợ từ 得 đứng ngay sau động từ 唱 để nối bổ ngữ mức độ.", "她 + 唱 + 得 + 非常好听.",
                     "Động từ + 得 + Cụm tính từ dùng để đánh giá mức độ hành động."),
                    ("sap_xep", "bo_ngu", "Sáng nay bạn đến sớm thật đấy.", ["今天早上", "你", "来", "得", "真早"], ["今天早上你来得真早", "你今天早上来得真早"],
                     "Trạng ngữ thời gian đứng đầu, theo sau là 你 + 来得 + 真早.", "来得真早 = đến thật sớm.",
                     "来得真早 nhận xét thời điểm thực hiện hành động rất sớm."),
                    ("sap_xep", "bo_ngu", "Em trai chạy nhanh hơn tôi.", ["弟弟", "跑", "得", "比我", "快"], ["弟弟跑得比我快"],
                     "Kết hợp bổ ngữ 得 và cấu trúc so sánh 比.", "弟弟 + 跑得 + 比我 + 快.",
                     "跑得比我快: chạy nhanh hơn tôi."),
                    ("dien_chu", "bo_ngu", "你汉语说___真不错！", "nǐ hànyǔ shuō ___ zhēn búcuò !",
                     "Tiếng Hán bạn nói thật là giỏi!",
                     ["得"], "Trợ từ kết cấu đứng sau động từ 说 và trước cụm đánh giá 真不错.", "Điền chữ 得 (de).",
                     "Khi động từ nối với lời đánh giá mức độ phía sau, bắt buộc dùng 得."),
                    ("sap_xep", "bo_ngu", "Tối qua tôi ngủ rất muộn.", ["昨天晚上", "我", "睡", "得", "很晚"], ["昨天晚上我睡得很晚", "我昨天晚上睡得很晚"],
                     "Động từ đơn âm 睡 đi liền với 得 + 很晚.", "昨天晚上 + 我 + 睡得很晚.",
                     "睡得很晚: đi ngủ rất muộn."),
                ],
            ),
            (
                "Câu cầu khiến 别 / 不要 và liên từ 因为…所以…",
                "Diễn đạt lời khuyên ngăn và quan hệ nguyên nhân – kết quả",
                [
                    ("sap_xep", "phu_dinh_nghi_van", "Trong lớp học đừng nói chuyện lớn tiếng.", ["在教室里", "别", "大声", "说话"], ["在教室里别大声说话"],
                     "Trạng ngữ nơi chốn 在教室里 mở đầu câu.", "Phó từ khuyên ngăn 别 đứng trước cụm động từ 大声说话.",
                     "别 + Động từ dùng để khuyên hoặc nhắc ai đừng làm gì."),
                    ("sap_xep", "lien_tu_quan_he", "Vì trời mưa nên chúng tôi không đi đá bóng.", ["因为", "下雨", "所以", "我们不去", "踢足球"], ["因为下雨所以我们不去踢足球"],
                     "Mệnh đề nguyên nhân mở đầu bằng 因为, mệnh đề kết quả mở đầu bằng 所以.", "因为下雨 + 所以 + 我们不去踢足球.",
                     "Cặp liên từ nhân quả 因为…所以… (vì… cho nên…)."),
                    ("dien_chu", "phu_dinh_nghi_van", "时间不早了，___看电视了。", "shíjiān bù zǎo le , ___ kàn diànshì le .",
                     "Không còn sớm nữa, đừng xem tivi nữa.",
                     ["别"], "Từ khuyên ngăn đi cặp với 了 cuối câu: __…了.", "Điền chữ 别 (bié = đừng).",
                     "Cấu trúc 别…了 dùng để khuyên dừng một hành động."),
                    ("sap_xep", "lien_tu_quan_he", "Tuy hơi đắt nhưng chất lượng rất tốt.", ["虽然", "有点儿贵", "但是", "质量", "很好"], ["虽然有点儿贵但是质量很好"],
                     "Mệnh đề nhượng bộ dùng 虽然, mệnh đề chuyển ý dùng 但是.", "虽然有点儿贵 + 但是 + 质量很好.",
                     "虽然…但是… nối hai vế đối lập nghĩa."),
                    ("sap_xep", "chao_hoi_giao_tiep", "Bạn giới thiệu giúp tôi một khách sạn nhé.", ["请你", "给我", "介绍", "一个", "宾馆"], ["请你给我介绍一个宾馆"],
                     "请你 mở đầu lời nhờ vả lịch sự.", "请你 + 给我 + 介绍 + 一个宾馆.",
                     "给 A 介绍 B: giới thiệu B cho A."),
                ],
            ),
        ],
    },
    {
        "vi_tri": 2,
        "ten": "Trợ từ động thái 了 / 过 / 着 & câu so sánh 比",
        "muc_tieu": "Phân biệt chuẩn trải nghiệm đã từng (过), trạng thái tiếp diễn (着) và so sánh hơn (比)",
        "lessons": [
            (
                "Trải nghiệm trong quá khứ với 过",
                "Ghép câu khẳng định, phủ định 没…过 và câu hỏi với trợ từ 过",
                [
                    ("sap_xep", "tro_tu_dong_thai", "Tôi đã từng ăn vịt quay Bắc Kinh.", ["我", "吃", "过", "北京", "烤鸭"], ["我吃过北京烤鸭"],
                     "Trợ từ 过 đặt ngay sau động từ 吃.", "我 + 吃过 + 北京烤鸭.",
                     "Động từ + 过 biểu thị trải nghiệm đã từng có."),
                    ("sap_xep", "tro_tu_dong_thai", "Anh ấy chưa từng đến Việt Nam.", ["他", "没", "来", "过", "越南"], ["他没来过越南"],
                     "Phủ định trải nghiệm dùng 没 trước động từ và giữ nguyên 过.", "他 + 没来过 + 越南.",
                     "Phủ định của Động từ + 过 là 没 + Động từ + 过."),
                    ("dien_chu", "tro_tu_dong_thai", "你去___中国吗？", "nǐ qù ___ Zhōngguó ma ?",
                     "Bạn đã từng đi Trung Quốc chưa?",
                     ["过"], "Trợ từ chỉ kinh nghiệm đứng ngay sau động từ 去.", "Điền chữ 过 (guo = từng).",
                     "去过中国: đã từng đi Trung Quốc."),
                    ("sap_xep", "tro_tu_dong_thai", "Bộ phim đó tôi xem qua hai lần rồi.", ["那个电影", "我", "看过", "两次", "了"], ["那个电影我看过两次了", "我看过两次那个电影了"],
                     "Bổ ngữ tần suất 两次 đứng sau 看过.", "那个电影 + 我 + 看过 + 两次了.",
                     "看过两次: đã từng xem hai lần."),
                    ("sap_xep", "tro_tu_dong_thai", "Bạn đã từng nghe bài hát tiếng Trung này chưa?", ["你", "听过", "这首", "中文歌", "吗"], ["你听过这首中文歌吗"],
                     "Lượng từ của bài hát là 首 (这首中文歌).", "你 + 听过 + 这首中文歌 + 吗.",
                     "听过这首中文歌吗: đã từng nghe bài hát tiếng Trung này chưa?"),
                ],
            ),
            (
                "Trạng thái duy trì với 着 và đang diễn ra 正在",
                "Viết câu mô tả trang phục đang mặc và trạng thái sự vật",
                [
                    ("sap_xep", "tro_tu_dong_thai", "Hôm nay cô ấy đang mặc một chiếc áo sơ mi trắng.", ["她今天", "穿", "着", "一件", "白衬衫"], ["她今天穿着一件白衬衫"],
                     "Trợ từ 着 đứng ngay sau động từ 穿 để chỉ trạng thái đang mặc.", "她今天 + 穿着 + 一件白衬衫.",
                     "穿着 biểu thị trạng thái trang phục đang mặc trên người."),
                    ("sap_xep", "tro_tu_dong_thai", "Cửa phòng học đang mở.", ["教室", "的", "门", "开", "着"], ["教室的门开着"],
                     "Chủ ngữ 教室的门 đứng đầu câu.", "Động từ 开 + 着 diễn tả trạng thái cửa đang để mở.",
                     "门开着: cửa đang mở."),
                    ("dien_chu", "tro_tu_dong_thai", "他手里拿___一本书。", "tā shǒu lǐ ná ___ yì běn shū .",
                     "Trong tay anh ấy đang cầm một quyển sách.",
                     ["着"], "Trợ từ chỉ trạng thái duy trì đi ngay sau động từ 拿.", "Điền chữ 着 (zhe).",
                     "手里拿着…: trên tay đang cầm…"),
                    ("sap_xep", "tro_tu_dong_thai", "Bên ngoài trời đang có tuyết rơi.", ["外面", "正在", "下雪", "呢"], ["外面正在下雪呢"],
                     "Phó từ 正在 trước động từ kết hợp 呢 cuối câu chỉ hành động đang diễn ra.", "外面 + 正在 + 下雪 + 呢.",
                     "正在…呢 nhấn mạnh sự việc đang diễn ra ngay lúc nói."),
                    ("sap_xep", "tro_tu_dong_thai", "Bọn trẻ đang mỉm cười nói chuyện.", ["孩子们", "笑", "着", "说话"], ["孩子们笑着说话"],
                     "Động từ 1 + 着 làm trạng ngữ chỉ cách thức cho động từ 2.", "孩子们 + 笑着 + 说话.",
                     "笑着说话: vừa cười vừa nói chuyện."),
                ],
            ),
            (
                "Câu so sánh hơn với 比 và 没有",
                "Sắp xếp chuẩn vị trí của A, B, tính từ và mức độ 一点儿 / 得多",
                [
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Máy bay nhanh hơn tàu hỏa nhiều.", ["飞机", "比", "火车", "快", "得多"], ["飞机比火车快得多"],
                     "Cấu trúc A 比 B + Tính từ + 得多.", "飞机 + 比 + 火车 + 快得多.",
                     "Trong câu chữ 比 không dùng 很 trước tính từ; muốn nói 'hơn nhiều' thêm 得多 sau tính từ."),
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Hôm nay không lạnh bằng hôm qua.", ["今天", "没有", "昨天", "那么", "冷"], ["今天没有昨天那么冷"],
                     "So sánh kém dùng A 没有 B (+ 那么) + Tính từ.", "今天 + 没有 + 昨天 + 那么冷.",
                     "A 没有 B 冷: A không lạnh bằng B."),
                    ("dien_chu", "cau_so_sanh_nhan_manh", "哥哥___我高五公分。", "gēge ___ wǒ gāo wǔ gōngfēn .",
                     "Anh trai cao hơn tôi năm xăng-ti-mét.",
                     ["比"], "Giới từ dùng trong câu so sánh hơn giữa 哥哥 và 我.", "Điền chữ 比 (bǐ = so với, hơn).",
                     "A 比 B + Tính từ + Số lượng chênh lệch."),
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Quả táo này giống hệt quả táo kia.", ["这个苹果", "跟", "那个苹果", "一样", "大"], ["这个苹果跟那个苹果一样大"],
                     "So sánh ngang bằng dùng A 跟 B 一样 + Tính từ.", "这个苹果 + 跟 + 那个苹果 + 一样大.",
                     "A 跟 B 一样 + Tính từ: A và B như nhau về mặt nào đó."),
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Tàu điện ngầm rẻ hơn taxi một chút.", ["地铁", "比", "出租车", "便宜", "一点儿"], ["地铁比出租车便宜一点儿"],
                     "Cụm chỉ mức độ nhỏ 一点儿 luôn đặt SAU tính từ 便宜.", "地铁 + 比 + 出租车 + 便宜一点儿.",
                     "便宜一点儿: rẻ hơn một chút."),
                ],
            ),
            (
                "Tổng hợp Viết HSK 2 hoàn chỉnh",
                "Kết hợp thời lượng, so sánh và trợ từ động thái trong câu giao tiếp",
                [
                    ("sap_xep", "thoi_gian_lich_hen", "Còn mười phút nữa là bắt đầu tiết học.", ["还有", "十分钟", "就", "上课", "了"], ["还有十分钟就上课了"],
                     "Cấu trúc sắp xảy ra: 还有 + Thời gian + 就…了.", "还有十分钟 + 就 + 上课了.",
                     "还有…就…了 biểu thị chỉ còn bao lâu nữa thì sự việc diễn ra."),
                    ("sap_xep", "so_dem_luong_tu", "Xin cho tôi xem thử chiếc đồng hồ màu đen kia.", ["请让我", "看看", "那块", "黑色的", "手表"], ["请让我看看那块黑色的手表"],
                     "Lượng từ của đồng hồ đeo tay 手表 là 块.", "请让我 + 看看 + 那块黑色的手表.",
                     "Lặp lại động từ 看看 mang sắc thái nhẹ nhàng 'xem thử một chút'."),
                    ("dien_chu", "thoi_gian_lich_hen", "新的一年快___到了。", "xīn de yì nián kuài ___ dào le .",
                     "Năm mới sắp sửa đến rồi.",
                     ["要"], "Cấu trúc chỉ sự việc sắp xảy ra: 快__…了.", "Điền chữ 要 (yào) trong cụm 快要…了.",
                     "快要…了 biểu thị sự việc sắp diễn ra trong tương lai rất gần."),
                    ("sap_xep", "phu_dinh_nghi_van", "Sao hôm nay bạn lại thức dậy sớm thế?", ["你今天", "怎么", "起得", "这么", "早"], ["你今天怎么起得这么早"],
                     "怎么 đứng trước động từ dùng để hỏi nguyên nhân mang sắc thái ngạc nhiên.", "你今天 + 怎么 + 起得 + 这么早.",
                     "怎么 + Vị ngữ: sao lại … thế?"),
                    ("sap_xep", "gia_dinh_nghe_nghiep", "Mọi người đều đang chuẩn bị cho kỳ thi ngày mai.", ["大家", "都在", "准备", "明天的", "考试"], ["大家都在准备明天的考试"],
                     "Phó từ 都 đứng trước 在 + Động từ.", "大家 + 都在 + 准备 + 明天的考试.",
                     "都在准备: tất cả đều đang chuẩn bị."),
                ],
            ),
        ],
    },
]


def _insert_question(db, cap_id: int, topic_id: int, q_tuple: tuple) -> int:
    kind = q_tuple[0]
    if kind == "sap_xep":
        _, _, nghia_vi, pieces, accepted, gy1, gy2, gt = q_tuple
        stem = " / ".join(pieces)
        existing = db.execute(
            text("SELECT id FROM cau_hoi WHERE cap_do_id = :c AND ky_nang = 'viet' AND dang = 'sap_xep' AND dich_nghia = :dn LIMIT 1"),
            {"c": cap_id, "dn": nghia_vi},
        ).scalar_one_or_none()
        if existing:
            return int(existing)
        qid = next_root_id(db, "cau_hoi")
        db.execute(
            text("""
                INSERT INTO cau_hoi (
                    id, ma_goc_id, phien_ban, dang, cap_do_id, ky_nang, nhom_kien_thuc_id,
                    dung_on_luyen, dung_thi_thu, dung_dau_vao,
                    noi_dung, dich_nghia, goi_y, goi_y_2, giai_thich, nguon_noi_dung, trang_thai
                ) VALUES (
                    :id, :id, 1, 'sap_xep', :c, 'viet', :n,
                    1, 0, 1,
                    :nd, :dn, :g1, :g2, :gt, 'tu_soan', 'da_dang'
                )
            """),
            {"id": qid, "c": cap_id, "n": topic_id, "nd": stem, "dn": nghia_vi, "g1": gy1, "g2": gy2, "gt": gt},
        )
        for idx, p in enumerate(pieces, start=1):
            db.execute(
                text("INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung) VALUES (:q, 'lua_chon', :t, 0, :nd)"),
                {"q": qid, "t": idx, "nd": p},
            )
        for idx, acc in enumerate(accepted, start=1):
            db.execute(
                text("INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung) VALUES (:q, 'dap_an_chap_nhan', :t, 0, :nd)"),
                {"q": qid, "t": idx, "nd": acc},
            )
        return qid

    # dien_chu
    _, _, noi_dung, pinyin, nghia_vi, accepted, gy1, gy2, gt = q_tuple
    existing = db.execute(
        text("SELECT id FROM cau_hoi WHERE cap_do_id = :c AND ky_nang = 'viet' AND dang = 'dien_chu' AND noi_dung = :nd LIMIT 1"),
        {"c": cap_id, "nd": noi_dung},
    ).scalar_one_or_none()
    if existing:
        return int(existing)
    qid = next_root_id(db, "cau_hoi")
    db.execute(
        text("""
            INSERT INTO cau_hoi (
                id, ma_goc_id, phien_ban, dang, cap_do_id, ky_nang, nhom_kien_thuc_id,
                dung_on_luyen, dung_thi_thu, dung_dau_vao,
                noi_dung, pinyin, dich_nghia, goi_y, goi_y_2, giai_thich, nguon_noi_dung, trang_thai
            ) VALUES (
                :id, :id, 1, 'dien_chu', :c, 'viet', :n,
                1, 0, 0,
                :nd, :py, :dn, :g1, :g2, :gt, 'tu_soan', 'da_dang'
            )
        """),
        {"id": qid, "c": cap_id, "n": topic_id, "nd": noi_dung, "py": pinyin, "dn": nghia_vi, "g1": gy1, "g2": gy2, "gt": gt},
    )
    for idx, acc in enumerate(accepted, start=1):
        db.execute(
            text("INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung) VALUES (:q, 'dap_an_chap_nhan', :t, 0, :nd)"),
            {"q": qid, "t": idx, "nd": acc},
        )
    return qid


def _seed_level_writing(db, cap_id: int, topic_ids: dict[str, int], lands_spec: list[dict]) -> int:
    created_sets = 0
    for land_spec in lands_spec:
        existing_land = db.execute(
            text("""
                SELECT ma_goc_id FROM bo_de
                WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'viet' AND ten = :ten AND trang_thai = 'da_dang'
                LIMIT 1
            """),
            {"c": cap_id, "ten": land_spec["ten"]},
        ).scalar_one_or_none()

        if existing_land:
            land_root = int(existing_land)
        else:
            land_root = next_root_id(db, "bo_de")
            db.execute(
                text("""
                    INSERT INTO bo_de (id, ma_goc_id, phien_ban, loai, cap_do_id, ky_nang, ten, muc_tieu, vi_tri, trang_thai)
                    VALUES (:id, :id, 1, 'thua', :c, 'viet', :ten, :mt, :vt, 'da_dang')
                """),
                {"id": land_root, "c": cap_id, "ten": land_spec["ten"], "mt": land_spec["muc_tieu"], "vt": land_spec["vi_tri"]},
            )
            created_sets += 1

        all_land_qids: list[int] = []
        for l_idx, (l_ten, l_mt, q_specs) in enumerate(land_spec["lessons"], start=1):
            qids = [_insert_question(db, cap_id, topic_ids[q[1]], q) for q in q_specs]
            all_land_qids.extend(qids)

            ex_lesson = db.execute(
                text("SELECT id FROM bo_de WHERE loai = 'bai' AND thua_id = :t AND vi_tri = :vt AND trang_thai = 'da_dang' LIMIT 1"),
                {"t": land_root, "vt": l_idx},
            ).scalar_one_or_none()
            if not ex_lesson:
                lid = next_root_id(db, "bo_de")
                db.execute(
                    text("""
                        INSERT INTO bo_de (id, ma_goc_id, phien_ban, loai, thua_id, ten, muc_tieu, vi_tri, trang_thai)
                        VALUES (:id, :id, 1, 'bai', :t, :ten, :mt, :vt, 'da_dang')
                    """),
                    {"id": lid, "t": land_root, "ten": l_ten, "mt": l_mt, "vt": l_idx},
                )
                for pos, qid in enumerate(qids, start=1):
                    db.execute(
                        text("INSERT INTO bo_de_cau_hoi (bo_de_id, cau_hoi_id, thu_tu, la_cau_vi_du) VALUES (:b, :q, :t, 0)"),
                        {"b": lid, "q": qid, "t": pos},
                    )
                created_sets += 1

        # Bài kiểm tra cuối thửa (vi_tri = 5, 10 câu đại diện từ 4 bài trong thửa)
        ex_final = db.execute(
            text("SELECT id FROM bo_de WHERE loai = 'cuoi_thua' AND thua_id = :t AND vi_tri = 5 AND trang_thai = 'da_dang' LIMIT 1"),
            {"t": land_root},
        ).scalar_one_or_none()
        if not ex_final and len(all_land_qids) >= 10:
            fid = next_root_id(db, "bo_de")
            final_qids = all_land_qids[::2][:10]
            db.execute(
                text("""
                    INSERT INTO bo_de (id, ma_goc_id, phien_ban, loai, thua_id, ten, muc_tieu, vi_tri, trang_thai)
                    VALUES (:id, :id, 1, 'cuoi_thua', :t, :ten, :mt, 5, 'da_dang')
                """),
                {
                    "id": fid,
                    "t": land_root,
                    "ten": f"Kiểm tra cuối thửa: {land_spec['ten']}",
                    "mt": "Hoàn thành đúng 10/10 câu để mở thửa tiếp theo",
                },
            )
            for pos, qid in enumerate(final_qids, start=1):
                db.execute(
                    text("INSERT INTO bo_de_cau_hoi (bo_de_id, cau_hoi_id, thu_tu, la_cau_vi_du) VALUES (:b, :q, :t, 0)"),
                    {"b": fid, "q": qid, "t": pos},
                )
            created_sets += 1

    return created_sets


HSK4_LANDS = [
    {
        "vi_tri": 1,
        "ten": "Liên từ phức hợp & câu nhấn mạnh HSK 4",
        "muc_tieu": "Viết chuẩn các cấu trúc 不仅…而且…, 无论…都…, 既然…就… và câu chữ 把 / 被",
        "lessons": [
            (
                "Liên từ tăng tiến và điều kiện",
                "Sắp xếp câu phức với 不仅…而且…, 无论…都…, 只要…就…",
                [
                    ("sap_xep", "lien_tu_quan_he", "Anh ấy không những thông minh mà còn rất chăm chỉ.", ["他", "不仅", "聪明", "而且", "很努力"], ["他不仅聪明而且很努力"],
                     "Cùng một chủ ngữ 他 nên 不仅 đặt sau chủ ngữ.", "他 + 不仅聪明 + 而且很努力.",
                     "Khi hai vế chung chủ ngữ, chủ ngữ đứng trước 不仅."),
                    ("sap_xep", "lien_tu_quan_he", "Chỉ cần kiên trì thì nhất định sẽ thành công.", ["只要", "坚持下去", "就", "一定能", "成功"], ["只要坚持下去就一定能成功"],
                     "Mệnh đề điều kiện đủ mở đầu bằng 只要, vế kết quả dùng 就.", "只要坚持下去 + 就一定能成功.",
                     "只要…就…: chỉ cần … thì …"),
                    ("sap_xep", "lien_tu_quan_he", "Đã hứa với người khác thì phải giữ lời.", ["既然", "答应了别人", "就", "应该", "守信用"], ["既然答应了别人就应该守信用"],
                     "既然 nêu tiền đề đã có thật, 就 dẫn ra kết luận hợp lý.", "既然答应了别人 + 就应该守信用.",
                     "既然…就…: đã … thì nên …"),
                    ("dien_chu", "lien_tu_quan_he", "无___遇到什么问题，都不要紧张。", "wú ___ yùdào shénme wèntí , dōu búyào jǐnzhāng .",
                     "Bất luận gặp phải vấn đề gì cũng đừng căng thẳng.",
                     ["论"], "Từ ghép với 无 tạo thành liên từ 'bất luận': 无__…都…", "Điền chữ 论 (lùn) trong 无论.",
                     "无论…都…: bất kể / cho dù … đều …"),
                    ("sap_xep", "lien_tu_quan_he", "Cho dù bận đến mấy cũng phải chú ý sức khỏe.", ["即使", "工作再忙", "也", "要注意", "身体"], ["即使工作再忙也要注意身体"],
                     "Cặp liên từ nhượng bộ giả thiết 即使…也…", "即使工作再忙 + 也要注意身体.",
                     "即使…也…: cho dù … cũng …"),
                ],
            ),
            (
                "Câu chữ 把 và câu bị động chữ 被",
                "Đặt đúng vị trí phó từ phủ định, trạng ngữ và bổ ngữ trong câu 把 / 被",
                [
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Xin hãy dọn dẹp phòng khách cho sạch sẽ.", ["请", "把", "客厅", "整理", "干净"], ["请把客厅整理干净"],
                     "Câu cầu khiến chữ 把: 请 + 把 + Tân ngữ + Động từ + Bổ ngữ kết quả.", "请 + 把客厅 + 整理干净.",
                     "整理干净: dọn dẹp sạch sẽ."),
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Vé máy bay ngày mai đã được đặt xong rồi.", ["明天的机票", "已经", "被", "订好", "了"], ["明天的机票已经被订好了"],
                     "Phó từ thời gian 已经 luôn đặt TRƯỚC chữ 被.", "明天的机票 + 已经 + 被 + 订好了.",
                     "Phó từ (已经, 没, 不) đứng trước 把 / 被."),
                    ("dien_chu", "cau_so_sanh_nhan_manh", "他不小心___护照弄丢了。", "tā bù xiǎoxīn ___ hùzhào nòng diū le .",
                     "Anh ấy vô ý làm mất hộ chiếu rồi.",
                     ["把"], "Giới từ đưa tân ngữ xác định 护照 lên trước động từ 弄丢.", "Điền chữ 把 (bǎ).",
                     "把护照弄丢了: làm mất cuốn hộ chiếu."),
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Đừng để rác thải làm ô nhiễm môi trường.", ["不要", "让垃圾", "污染", "了", "环境"], ["不要让垃圾污染了环境"],
                     "Câu kiêm ngữ khuyên ngăn mở đầu bằng 不要.", "不要 + 让垃圾 + 污染了环境.",
                     "污染环境: làm ô nhiễm môi trường."),
                    ("sap_xep", "cau_so_sanh_nhan_manh", "Tài liệu họp tôi đã gửi vào hộp thư của ngài rồi.", ["会议材料", "我", "已经发到", "您的邮箱", "了"], ["会议材料我已经发到您的邮箱了", "我已经把会议材料发到您的邮箱了"],
                     "Đưa đối tượng 会议材料 lên đầu câu nhấn mạnh chủ đề.", "会议材料 + 我 + 已经发到 + 您的邮箱了.",
                     "发到邮箱: gửi tới hộp thư điện tử."),
                ],
            ),
            (
                "Bổ ngữ xu hướng mở rộng & mức độ",
                "Vận dụng 起来, 下去, 出来 trong nghĩa bóng HSK 4",
                [
                    ("sap_xep", "bo_ngu", "Thời tiết dần dần ấm áp lên rồi.", ["天气", "渐渐", "暖和", "起来", "了"], ["天气渐渐暖和起来了"],
                     "Tính từ + 起来 biểu thị trạng thái bắt đầu xuất hiện và tăng dần.", "天气 + 渐渐 + 暖和起来了.",
                     "暖和起来: bắt đầu ấm dần lên."),
                    ("sap_xep", "bo_ngu", "Giọng nói này nghe ra là của giám đốc Vương.", ["这个声音", "听出来", "是", "王经理", "的"], ["这个声音听出来是王经理的"],
                     "听出来 mang nghĩa nhận ra qua việc nghe.", "这个声音 + 听出来 + 是王经理的.",
                     "Động từ + 出来 chỉ sự nhận biết / phát hiện ra."),
                    ("dien_chu", "bo_ngu", "他累___连话都不想说了。", "tā lèi ___ lián huà dōu bù xiǎng shuō le .",
                     "Anh ấy mệt đến mức ngay cả nói cũng chẳng muốn nói nữa.",
                     ["得"], "Trợ từ kết cấu nối tính từ 累 với cụm bổ ngữ mức độ phía sau.", "Điền chữ 得 (de).",
                     "累得…: mệt đến nỗi…"),
                    ("sap_xep", "bo_ngu", "Kế hoạch này e rằng rất khó thực hiện được.", ["这个计划", "恐怕", "很难", "实现", "得了"], ["这个计划恐怕很难实现得了"],
                     "Phó từ phỏng đoán 恐怕 đứng trước 很难.", "这个计划 + 恐怕 + 很难 + 实现得了.",
                     "实现 (shíxiàn): thực hiện / hiện thực hóa."),
                    ("sap_xep", "lien_tu_quan_he", "Ngược lại cách làm này lại tiết kiệm được nhiều thời gian hơn.", ["这样做", "反而", "能节约", "更多", "时间"], ["这样做反而能节约更多时间"],
                     "Phó từ 反而 nối kết quả trái ngược dự đoán.", "这样做 + 反而 + 能节约 + 更多时间.",
                     "反而: trái lại / ngược lại còn…"),
                ],
            ),
            (
                "Diễn đạt công việc và xã hội HSK 4",
                "Sắp xếp câu trang trọng trong môi trường học thuật và công sở",
                [
                    ("sap_xep", "gia_dinh_nghe_nghiep", "Kinh nghiệm phong phú giúp anh ấy nhận được công việc này.", ["丰富的经验", "使他", "获得了", "这份", "工作"], ["丰富的经验使他获得了这份工作"],
                     "Cấu trúc kiêm ngữ trang trọng dùng động từ 使 (khiến cho/giúp cho).", "丰富的经验 + 使他 + 获得了 + 这份工作.",
                     "获得这份工作: giành/nhận được công việc này."),
                    ("sap_xep", "thoi_gian_lich_hen", "Chuyến bay đi Thượng Hải bị hoãn lại một tiếng.", ["飞往上海的", "航班", "推迟了", "一个", "小时"], ["飞往上海的航班推迟了一个小时"],
                     "Định ngữ 飞往上海的 đứng trước danh từ trung tâm 航班.", "飞往上海的航班 + 推迟了 + 一个小时.",
                     "推迟 (tuīchí): hoãn lại, lùi thời gian."),
                    ("dien_chu", "chao_hoi_giao_tiep", "我完全同___你的看法。", "wǒ wánquán tóng ___ nǐ de kànfǎ .",
                     "Tôi hoàn toàn đồng ý với quan điểm của bạn.",
                     ["意"], "Động từ 'đồng ý' gồm chữ 同 ghép với chữ gì?", "Điền chữ 意 (yì) tạo thành 同意.",
                     "同意看法: đồng ý với cách nhìn / quan điểm."),
                    ("sap_xep", "so_dem_luong_tu", "Hơn tám mươi phần trăm sinh viên đều tán thành phương án này.", ["超过百分之八十的", "学生", "都赞成", "这个", "方案"], ["超过百分之八十的学生都赞成这个方案"],
                     "Cụm phần trăm làm định ngữ đứng trước 学生.", "超过百分之八十的学生 + 都赞成 + 这个方案.",
                     "百分之 + số: phần trăm (%)."),
                    ("sap_xep", "phu_dinh_nghi_van", "Thành công chưa bao giờ là chuyện dễ dàng.", ["成功", "从来", "都不是", "一件", "容易的事"], ["成功从来都不是一件容易的事"],
                     "Phó từ 从来 đi với phủ định 都不是.", "成功 + 从来 + 都不是 + 一件容易的事.",
                     "从来不/没…: xưa nay chưa từng / không bao giờ…"),
                ],
            ),
        ],
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        topic_ids = {r["ma"]: int(r["id"]) for r in db.execute(text("SELECT id, ma FROM nhom_kien_thuc")).mappings().all()}
        cap_ids = {r["ma"]: int(r["id"]) for r in db.execute(text("SELECT id, ma FROM cap_do")).mappings().all()}

        c1 = _seed_level_writing(db, cap_ids["HSK1"], topic_ids, HSK1_LANDS)
        c2 = _seed_level_writing(db, cap_ids["HSK2"], topic_ids, HSK2_LANDS)
        c4 = _seed_level_writing(db, cap_ids["HSK4"], topic_ids, HSK4_LANDS)
        db.commit()
        print(f"SEED_VIET_ALL_LEVELS_OK: +{c1} HSK1, +{c2} HSK2, +{c4} HSK4 sets")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
