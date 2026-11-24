"""Nạp bổ sung Từ vựng chuẩn HSK 3–4 kèm câu ví dụ và Lộ trình Ôn luyện Từ vựng HSK 3–4.

- HSK 3: Bổ sung ví dụ cho các từ chưa có ví dụ + thêm 2 thửa mới (40 từ HSK 3 chuẩn + 60 câu ôn luyện có gợi ý 2 bậc).
- HSK 4: Thêm 120 từ vựng HSK 4 cốt lõi (đầy đủ chữ Hán, Pinyin, nghĩa Việt, câu ví dụ + Pinyin + dịch nghĩa)
  và 4 thửa Ôn luyện Từ vựng HSK 4 (mỗi thửa 4 bài × 5 câu + 1 bài Kiểm tra cuối thửa × 10 câu = 120 câu ôn luyện).
- An toàn khi chạy lại nhiều lần (idempotent).
"""
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.practice_authoring.services import path_service
from app.modules.questions.schemas.question_payload import QuestionIn
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

# Bổ sung ví dụ cho 60 từ HSK 3 hiện có nếu đang trống vd_cau
HSK3_EXISTING_EXAMPLES = {
    "鼻子": ("他感冒了，鼻子有点儿不舒服。", "Tā gǎnmào le, bízi yǒudiǎnr bù shūfu.", "Anh ấy bị cảm rồi, mũi hơi khó chịu."),
    "耳朵": ("兔子的耳朵长长的，非常可爱。", "Tùzi de ěrduo chángcháng de, fēicháng kě'ài.", "Tai của thỏ dài dài, vô cùng đáng yêu."),
    "头发": ("妹妹的头发又黑又长。", "Mèimei de tóufa yòu hēi yòu cháng.", "Tóc của em gái vừa đen vừa dài."),
    "腿": ("爬了一天山，我的腿很疼。", "Pále yì tiān shān, wǒ de tuǐ hěn téng.", "Leo núi cả ngày, chân tôi rất đau."),
    "嘴": ("吃饭的时候别张着嘴说话。", "Chīfàn de shíhou bié zhāngzhe zuǐ shuōhuà.", "Lúc ăn cơm đừng há miệng nói chuyện."),
    "感冒": ("天气冷了，小心别感冒。", "Tiānqì lěng le, xiǎoxīn bié gǎnmào.", "Trời lạnh rồi, cẩn thận kẻo bị cảm."),
    "发烧": ("孩子有点儿发烧，我们去医院吧。", "Háizi yǒudiǎnr fāshāo, wǒmen qù yīyuàn ba.", "Đứa bé hơi sốt rồi, chúng mình đi bệnh viện nhé."),
    "疼": ("我今天头疼，想早点儿休息。", "Wǒ jīntiān tóu téng, xiǎng zǎodiǎnr xiūxi.", "Hôm nay tôi đau đầu, muốn nghỉ ngơi sớm một chút."),
    "健康": ("每天运动对身体健康很有帮助。", "Měitiān yùndòng duì shēntǐ jiànkāng hěn yǒu bāngzhù.", "Vận động mỗi ngày rất có ích cho sức khỏe."),
    "锻炼": ("爷爷每天早上都去公园锻炼身体。", "Yéye měitiān zǎoshang dōu qù gōngyuán duànliàn shēntǐ.", "Ông nội sáng nào cũng ra công viên tập thể dục."),
    "矮": ("弟弟去年很矮，今年长高了不少。", "Dìdi qùnián hěn ǎi, jīnnián zhǎng gāo le bù shǎo.", "Em trai năm ngoái rất thấp, năm nay cao lên nhiều rồi."),
    "胖": ("这只小猫吃得太多，越来越胖了。", "Zhè zhī xiǎo māo chī de tài duō, yuèláiyuè pàng le.", "Chú mèo nhỏ này ăn nhiều quá, ngày càng béo lên."),
    "瘦": ("她最近工作很忙，瘦了三公斤。", "Tā zuìjìn gōngzuò hěn máng, shòu le sān gōngjīn.", "Gần đây cô ấy bận việc quá, gầy đi ba cân."),
    "聪明": ("这个小男孩儿又聪明又懂礼貌。", "Zhège xiǎo nánháir yòu cōngming yòu dǒng lǐmào.", "Cậu bé này vừa thông minh vừa lễ phép."),
    "可爱": ("邻居家的女儿笑起来真可爱。", "Línjū jiā de nǚ'ér xiào qǐlái zhēn kě'ài.", "Con gái nhà hàng xóm lúc cười trông thật đáng yêu."),
    "担心": ("请别担心，我已经安全到家了。", "Qǐng bié dānxīn, wǒ yǐjīng ānquán dào jiā le.", "Xin đừng lo lắng, tôi đã về đến nhà an toàn rồi."),
    "害怕": ("晚上一个人在家，她有点儿害怕。", "Wǎnshang yígè rén zài jiā, tā yǒudiǎnr hàipà.", "Buổi tối ở nhà một mình, cô ấy hơi sợ."),
    "生气": ("我不是故意的，你别生气了。", "Wǒ bú shì gùyì de, nǐ bié shēngqì le.", "Tôi không cố ý đâu, bạn đừng giận nữa."),
    "满意": ("经理对我们这次的计划非常满意。", "Jīnglǐ duì wǒmen zhè cì de jìhuà fēicháng mǎnyì.", "Giám đốc rất hài lòng với kế hoạch lần này của chúng tôi."),
    "着急": ("离火车开还有半个小时，别着急。", "Lí huǒchē kāi hái yǒu bàn gè xiǎoshí, bié zháojí.", "Còn nửa tiếng nữa tàu mới chạy, đừng sốt ruột."),
    "冰箱": ("妈妈把新鲜水果放进了冰箱里。", "Māma bǎ xīnxiān shuǐguǒ fàng jìn le bīngxiāng lǐ.", "Mẹ đã cất hoa quả tươi vào trong tủ lạnh."),
    "空调": ("房间里太热了，请把空调打开吧。", "Fángjiān lǐ tài rè le, qǐng bǎ kōngtiáo dǎkāi ba.", "Trong phòng nóng quá, vui lòng bật điều hòa lên nhé."),
    "灯": ("离开教室以前，请记得关灯。", "Líkāi jiàoshì yǐqián, qǐng jìde guān dēng.", "Trước khi rời phòng học, hãy nhớ tắt đèn."),
    "碗": ("晚饭以后，弟弟主动去洗碗。", "Wǎnfàn yǐhòu, dìdi zhǔdòng qù xǐ wǎn.", "Sau bữa tối, em trai chủ động đi rửa bát."),
    "筷子": ("很多外国人也会用筷子吃中国菜。", "Hěn duō wàiguórén yě huì yòng kuàizi chī Zhōngguó cài.", "Nhiều người nước ngoài cũng biết dùng đũa ăn món Trung Quốc."),
    "衬衫": ("这件白衬衫很适合你上班穿。", "Zhè jiàn bái chènshān hěn shìhé nǐ shàngbān chuān.", "Chiếc áo sơ mi trắng này rất hợp để bạn mặc đi làm."),
    "裤子": ("这条黑裤子有点儿长，有短一点儿的吗？", "Zhè tiáo hēi kùzi yǒudiǎnr cháng, yǒu duǎn yìdiǎnr de ma?", "Chiếc quần đen này hơi dài, có chiếc nào ngắn hơn chút không?"),
    "裙子": ("姐姐买了一条漂亮的红裙子。", "Jiějie mǎi le yì tiáo piàoliang de hóng qúnzi.", "Chị gái đã mua một chiếc váy đỏ rất đẹp."),
    "帽子": ("外面风很大，戴上帽子再出门吧。", "Wàimiàn fēng hěn dà, dài shàng màozi zài chūmén ba.", "Bên ngoài gió to lắm, đội mũ vào rồi hẵng ra ngoài."),
    "皮鞋": ("爸爸擦干净了那双黑皮鞋。", "Bàba cā gānjìng le nà shuāng hēi píxié.", "Bố đã đánh sạch đôi giày da màu đen đó."),
    "伞": ("今天下午可能会下雨，你带把伞吧。", "Jīntiān xiàwǔ kěnéng huì xiàyǔ, nǐ dài bǎ sǎn ba.", "Chiều nay có thể sẽ mưa, bạn mang theo chiếc ô nhé."),
    "护照": ("去国外旅游一定要带好护照。", "Qù guówài lǚyóu yídìng yào dài hǎo hùzhào.", "Đi du lịch nước ngoài nhất định phải mang kỹ hộ chiếu."),
    "照相机": ("我用照相机拍了很多美丽的风景。", "Wǒ yòng zhàoxiàngjī pāi le hěn duō měilì de fēngjǐng.", "Tôi đã dùng máy ảnh chụp rất nhiều phong cảnh đẹp."),
    "行李箱": ("这个行李箱太重了，我帮您拿吧。", "Zhège xínglixiāng tài zhòng le, wǒ bāng nín ná ba.", "Chiếc vali này nặng quá, để tôi xách giúp ngài nhé."),
    "笔记本": ("请把重要的生词记在笔记本上。", "Qǐng bǎ zhòngyào de shēngcí jì zài bǐjìběn shàng.", "Hãy ghi các từ mới quan trọng vào sổ tay."),
    "打扫": ("周末我们一起把房间打扫干净了。", "Zhōumò wǒmen yìqǐ bǎ fángjiān dǎsǎo gānjìng le.", "Cuối tuần chúng tôi cùng nhau dọn dẹp sạch sẽ căn phòng."),
    "洗澡": ("跑完步先休息一会儿再去洗澡。", "Pǎo wán bù xiān xiūxi yíhuìr zài qù xǐzǎo.", "Chạy bộ xong hãy nghỉ một lát rồi mới đi tắm."),
    "刷牙": ("每天早晚都要认真刷牙。", "Měitiān zǎowǎn dōu yào rènzhēn shuāyá.", "Mỗi sáng tối đều phải đánh răng kỹ càng."),
    "搬": ("下个月我们家要搬到地铁站附近。", "Xià gè yuè wǒmen jiā yào bān dào dìtiězhàn fùjìn.", "Tháng sau nhà chúng tôi sẽ chuyển đến gần ga tàu điện ngầm."),
    "照顾": ("妈妈生病的时候，爸爸一直照顾她。", "Māma shēngbìng de shíhou, bàba yìzhí zhàogu tā.", "Lúc mẹ ốm, bố luôn chăm sóc cho mẹ."),
    "超市": ("我家楼下新开了一家大超市。", "Wǒ jiā lóuxià xīn kāi le yì jiā dà chāoshì.", "Dưới lầu nhà tôi mới mở một siêu thị lớn."),
    "银行": ("请问，附近哪儿有中国银行？", "Qǐngwèn, fùjìn nǎr yǒu Zhōngguó Yínháng?", "Xin hỏi, gần đây ở đâu có Ngân hàng Trung Quốc?"),
    "图书馆": ("周末很多学生在图书馆安静地看书。", "Zhōumò hěn duō xuésheng zài túshūguǎn ānjìng de kànshū.", "Cuối tuần nhiều sinh viên đọc sách yên tĩnh trong thư viện."),
    "地铁": ("早上坐地铁上班比坐公共汽车快。", "Zǎoshang zuò dìtiě shàngbān bǐ zuò gōnggòng qìchē kuài.", "Buổi sáng đi tàu điện ngầm đi làm nhanh hơn đi xe buýt."),
    "电梯": ("会议室在十二层，我们坐电梯上去吧。", "Huìyìshì zài shí'èr céng, wǒmen zuò diàntī shàngqù ba.", "Phòng họp ở tầng 12, chúng ta đi thang máy lên nhé."),
    "春": ("春天来了，公园里的花都开了。", "Chūntiān lái le, gōngyuán lǐ de huā dōu kāi le.", "Mùa xuân đến rồi, hoa trong công viên đều nở cả rồi."),
    "夏": ("北京的夏天有时候非常热。", "Běijīng de xiàtiān yǒushíhou fēicháng rè.", "Mùa hè ở Bắc Kinh đôi khi rất nóng."),
    "秋": ("秋天是去北京看红叶最好的季节。", "Qiūtiān shì qù Běijīng kàn hóngyè zuì hǎo de jìjié.", "Mùa thu là mùa đẹp nhất để đi Bắc Kinh ngắm lá đỏ."),
    "冬": ("北方的冬天常常下大雪。", "Běifāng de dōngtiān chángcháng xià dà xuě.", "Mùa đông ở miền Bắc thường có tuyết rơi dày."),
    "太阳": ("雨停了，太阳从云里出来了。", "Yǔ tíng le, tàiyáng cóng yún lǐ chūlái le.", "Mưa tạnh rồi, mặt trời ló ra khỏi đám mây."),
    "熊猫": ("孩子们最喜欢去动物园看大熊猫。", "Háizimen zuì xǐhuan qù dòngwùyuán kàn dà xióngmāo.", "Trẻ em thích nhất là đi sở thú xem gấu trúc lớn."),
    "鸟": ("树上有几只小鸟在唱歌。", "Shù shàng yǒu jǐ zhī xiǎo niǎo zài chànggē.", "Trên cây có mấy chú chim nhỏ đang hót."),
    "马": ("草原上有很多马在跑。", "Cǎoyuán shàng yǒu hěn duō mǎ zài pǎo.", "Trên thảo nguyên có rất nhiều ngựa đang chạy."),
    "树": ("学校门口种着一排高大的树。", "Xuéxiào ménkǒu zhòngzhe yì pái gāodà de shù.", "Trước cổng trường trồng một hàng cây cao lớn."),
    "草": ("请不要站在公园的草地上。", "Qǐng búyào zhàn zài gōngyuán de cǎodì shàng.", "Xin đừng đứng lên bãi cỏ trong công viên."),
    "数学": ("他的数学成绩一直排在班里第一名。", "Tā de shùxué chéngjì yìzhí pái zài bān lǐ dì-yī míng.", "Điểm môn Toán của cậu ấy luôn đứng nhất lớp."),
    "历史": ("我对中国的历史和文化很感兴趣。", "Wǒ duì Zhōngguó de lìshǐ hé wénhuà hěn gǎn xìngqù.", "Tôi rất có hứng thú với lịch sử và văn hóa Trung Quốc."),
    "作业": ("做完今天的作业再去看电视。", "Zuò wán jīntiān de zuòyè zài qù kàn diànshì.", "Làm xong bài tập hôm nay rồi mới đi xem tivi."),
    "复习": ("明天有考试，今晚我要好好复习。", "Míngtiān yǒu kǎoshì, jīnwǎn wǒ yào hǎohǎo fùxí.", "Ngày mai có bài thi, tối nay tôi phải ôn tập thật kỹ."),
    "成绩": ("经过努力，她的汉语成绩提高了很多。", "Jīngguò nǔlì, tā de Hànyǔ chéngjì tígāo le hěn duō.", "Nhờ nỗ lực, thành tích tiếng Hán của cô ấy đã nâng cao rất nhiều."),
}

# 2 thửa mới cho HSK 3 Từ vựng (40 từ)
HSK3_NEW_LANDS = [
    {
        "ten": "Giao tiếp, công việc và kế hoạch",
        "muc_tieu": "Nắm vững từ vựng HSK 3 về công sở, cuộc họp, kế hoạch và giải quyết vấn đề",
        "nhom_ma": "thoi_gian_lich_hen",
        "bai": [
            ("Cuộc họp và công sở", [
                ("会议", "huìyì", "cuộc họp, hội nghị", "下午两点有一个重要的部门会议。", "Xiàwǔ liǎng diǎn yǒu yígè zhòngyào de bùmén huìyì.", "Hai giờ chiều có một cuộc họp phòng ban quan trọng."),
                ("经理", "jīnglǐ", "giám đốc, quản lý", "王经理正在办公室里看文件。", "Wáng jīnglǐ zhèngzài bàngōngshì lǐ kàn wénjiàn.", "Giám đốc Vương đang xem tài liệu trong văn phòng."),
                ("同事", "tóngshì", "đồng nghiệp", "新来的同事对大家都非常热情。", "Xīn lái de tóngshì duì dàjiā dōu fēicháng rèqíng.", "Đồng nghiệp mới đến rất nhiệt tình với mọi người."),
                ("办公室", "bàngōngshì", "văn phòng", "请问李老师的办公室在几层？", "Qǐngwèn Lǐ lǎoshī de bàngōngshì zài jǐ céng?", "Xin hỏi văn phòng của thầy Lý ở tầng mấy?"),
                ("帮忙", "bāngmáng", "giúp đỡ", "多亏你来帮忙，我们才按时做完。", "Duōkuī nǐ lái bāngmáng, wǒmen cái ànshí zuò wán.", "Nhờ bạn đến giúp đỡ nên chúng tôi mới làm xong đúng hạn."),
            ]),
            ("Lựa chọn và quyết định", [
                ("决定", "juédìng", "quyết định", "我们决定今年夏天去云南旅游。", "Wǒmen juédìng jīnnián xiàtiān qù Yúnnán lǚyóu.", "Chúng tôi quyết định mùa hè năm nay đi du lịch Vân Nam."),
                ("选择", "xuǎnzé", "lựa chọn", "面对这两个机会，他不知道怎么选择。", "Miànduì zhè liǎng gè jīhuì, tā bù zhīdào zěnme xuǎnzé.", "Đứng trước hai cơ hội này, anh ấy không biết chọn thế nào."),
                ("同意", "tóngyì", "đồng ý", "爸爸妈妈都同意我参加这次夏令营。", "Bàba māma dōu tóngyì wǒ cānjiā zhè cì xiàlìngyíng.", "Bố mẹ đều đồng ý cho tôi tham gia trại hè lần này."),
                ("相信", "xiāngxìn", "tin tưởng", "我相信只要努力就一定能成功。", "Wǒ xiāngxìn zhǐyào nǔlì jiù yídìng néng chénggōng.", "Tôi tin rằng chỉ cần nỗ lực thì nhất định sẽ thành công."),
                ("了解", "liǎojiě", "hiểu rõ, tìm hiểu", "来中国以前，他已经了解了不少中国习惯。", "Lái Zhōngguó yǐqián, tā yǐjīng liǎojiě le bù shǎo Zhōngguó xíguàn.", "Trước khi đến Trung Quốc, anh ấy đã tìm hiểu khá nhiều thói quen Trung Quốc."),
            ]),
            ("Yêu cầu và giải quyết", [
                ("要求", "yāoqiú", "yêu cầu", "老师对我们的发音要求很严格。", "Lǎoshī duì wǒmen de fāyīn yāoqiú hěn yángé.", "Thầy giáo yêu cầu rất nghiêm khắc về phát âm của chúng tôi."),
                ("解决", "jiějué", "giải quyết", "这个问题我们已经找到办法解决了。", "Zhège wèntí wǒmen yǐjīng zhǎodào bànfǎ jiějué le.", "Vấn đề này chúng tôi đã tìm ra cách giải quyết rồi."),
                ("办法", "bànfǎ", "cách làm, biện pháp", "你有什么好办法能提高口语水平吗？", "Nǐ yǒu shénme hǎo bànfǎ néng tígāo kǒuyǔ shuǐpíng ma?", "Bạn có cách hay nào để nâng cao trình độ khẩu ngữ không?"),
                ("完成", "wánchéng", "hoàn thành", "他在星期五以前完成了所有的工作。", "Tā zài xīngqīwǔ yǐqián wánchéng le suǒyǒu de gōngzuò.", "Anh ấy đã hoàn thành toàn bộ công việc trước thứ Sáu."),
                ("机会", "jīhuì", "cơ hội", "这是一次很好的学习机会，别错过。", "Zhè shì yí cì hěn hǎo de xuéxí jīhuì, bié cuòguò.", "Đây là một cơ hội học tập rất tốt, đừng bỏ lỡ."),
            ]),
            ("Thay đổi và thói quen", [
                ("习惯", "xíguàn", "thói quen; quen với", "我已经习惯了早睡早起的生活。", "Wǒ yǐjīng xíguàn le zǎoshuì zǎoqǐ de shēnghuó.", "Tôi đã quen với nếp sống ngủ sớm dậy sớm rồi."),
                ("变化", "biànhuà", "sự thay đổi, biến đổi", "这几年我的家乡发生了很大的变化。", "Zhè jǐ nián wǒ de jiāxiāng fāshēng le hěn dà de biànhuà.", "Mấy năm nay quê hương tôi đã có sự thay đổi rất lớn."),
                ("参加", "cānjiā", "tham gia", "下周学校举行运动会，你想参加吗？", "Xià zhōu xuéxiào jǔxíng yùndònghuì, nǐ xiǎng cānjiā ma?", "Tuần sau trường tổ chức hội thao, bạn có muốn tham gia không?"),
                ("迟到", "chídào", "đến muộn", "今天路上堵车，我差点儿迟到了。", "Jīntiān lùshang dǔchē, wǒ chàdiǎnr chídào le.", "Hôm nay trên đường tắc xe, tôi suýt nữa thì đến muộn."),
                ("重要", "zhòngyào", "quan trọng", "休息和学习一样重要，要注意身体。", "Xiūxi hé xuéxí yíyàng zhòngyào, yào zhùyì shēntǐ.", "Nghỉ ngơi cũng quan trọng như học tập, phải chú ý sức khỏe."),
            ]),
        ],
    },
    {
        "ten": "Văn hóa, mua sắm và đời sống số",
        "muc_tieu": "Sử dụng từ vựng HSK 3 về lễ tết, âm nhạc, ẩm thực và liên lạc trực tuyến",
        "nhom_ma": "chao_hoi_giao_tiep",
        "bai": [
            ("Văn hóa và lễ hội", [
                ("节日", "jiérì", "ngày lễ, lễ hội", "春节是中国最重要的传统节日。", "Chūnjié shì Zhōngguó zuì zhòngyào de chuántǒng jiérì.", "Tết Nguyên đán là ngày lễ truyền thống quan trọng nhất của Trung Quốc."),
                ("礼物", "lǐwù", "món quà", "过生日的时候，朋友送给我一件礼物。", "Guò shēngrì de shíhou, péngyou sòng gěi wǒ yí jiàn lǐwù.", "Lúc đón sinh nhật, bạn bè tặng tôi một món quà."),
                ("节目", "jiémù", "chương trình, tiết mục", "今晚的电视节目非常有意思。", "Jīnwǎn de diànshì jiémù fēicháng yǒu yìsi.", "Chương trình truyền hình tối nay vô cùng thú vị."),
                ("音乐", "yīnyuè", "âm nhạc", "做完工作后，她喜欢听安静的音乐。", "Zuò wán gōngzuò hòu, tā xǐhuan tīng ānjìng de yīnyuè.", "Sau khi làm xong việc, cô ấy thích nghe nhạc nhẹ nhàng."),
                ("故事", "gùshi", "câu chuyện", "奶奶讲的那个老故事真感人。", "Nǎinai jiǎng de nàge lǎo gùshi zhēn gǎnrén.", "Câu chuyện xưa mà bà nội kể thật cảm động."),
            ]),
            ("Ẩm thực và mua sắm", [
                ("菜单", "càidān", "thực đơn", "服务员，请给我们看一下菜单。", "Fúwùyuán, qǐng gěi wǒmen kàn yíxià càidān.", "Phục vụ ơi, vui lòng cho chúng tôi xem thực đơn một chút."),
                ("果汁", "guǒzhī", "nước ép trái cây", "夏天喝一杯冰果汁真舒服。", "Xiàtiān hē yì bēi bīng guǒzhī zhēn shūfu.", "Mùa hè uống một ly nước ép trái cây mát lạnh thật dễ chịu."),
                ("面包", "miànbāo", "bánh mì", "早餐我一般吃两片面包，喝一杯牛奶。", "Zǎocān wǒ yìbān chī liǎng piàn miànbāo, hē yì bēi niúnǎi.", "Bữa sáng tôi thường ăn hai lát bánh mì và uống một cốc sữa."),
                ("新鲜", "xīnxiān", "tươi, trong lành", "这家水果店的苹果又大又新鲜。", "Zhè jiā shuǐguǒdiàn de píngguǒ yòu dà yòu xīnxiān.", "Táo ở tiệm hoa quả này vừa to vừa tươi."),
                ("甜", "tián", "ngọt", "这块西瓜特别甜，你快尝一尝。", "Zhè kuài xīguā tèbié tián, nǐ kuài cháng yì cháng.", "Miếng dưa hấu này ngọt lắm, bạn mau nếm thử đi."),
            ]),
            ("Internet và thông tin", [
                ("上网", "shàngwǎng", "lên mạng", "现在人们每天都用手机上网查资料。", "Xiànzài rénmen měitiān dōu yòng shǒujī shàngwǎng chá zīliào.", "Bây giờ mọi người hằng ngày đều dùng điện thoại lên mạng tra tài liệu."),
                ("电子邮件", "diànzǐ yóujiàn", "thư điện tử (email)", "请把报告发到我的电子邮件里。", "Qǐng bǎ bàogào fā dào wǒ de diànzǐ yóujiàn lǐ.", "Vui lòng gửi báo cáo vào hộp thư điện tử của tôi."),
                ("新闻", "xīnwén", "tin tức, thời sự", "爸爸每天晚饭后都会看半小时新闻。", "Bàba měitiān wǎnfàn hòu dōu huì kàn bàn xiǎoshí xīnwén.", "Mỗi ngày sau bữa tối bố đều xem thời sự nửa tiếng."),
                ("词典", "cídiǎn", "từ điển", "遇到不认识的汉字可以查汉语词典。", "Yùdào bú rènshi de Hànzì kěyǐ chá Hànyǔ cídiǎn.", "Gặp chữ Hán không biết có thể tra từ điển tiếng Hán."),
                ("借", "jiè", "mượn, cho mượn", "我今天去学校图书馆借了三本书。", "Wǒ jīntiān qù xuéxiào túshūguǎn jiè le sān běn shū.", "Hôm nay tôi đến thư viện trường mượn ba cuốn sách."),
            ]),
            ("Trạng thái và nhận xét", [
                ("安静", "ānjìng", "yên tĩnh", "这家咖啡店很安静，适合看书学习。", "Zhè jiā kāfēidiàn hěn ānjìng, shìhé kànshū xuéxí.", "Quán cà phê này rất yên tĩnh, hợp để đọc sách học bài."),
                ("干净", "gānjìng", "sạch sẽ", "妈妈把所有的衣服都洗得干干净净。", "Māma bǎ suǒyǒu de yīfu dōu xǐ de gāngānjìngjìng.", "Mẹ đã giặt toàn bộ quần áo sạch tinh tươm."),
                ("方便", "fāngbiàn", "thuận tiện, tiện lợi", "住在这儿坐车和买东西都非常方便。", "Zhù zài zhèr zuòchē hé mǎi dōngxi dōu fēicháng fāngbiàn.", "Sống ở đây đi xe và mua đồ đều vô cùng thuận tiện."),
                ("简单", "jiǎndān", "đơn giản", "这道菜的做法很简单，十分钟就能做好。", "Zhè dào cài de zuòfǎ hěn jiǎndān, shí fēnzhōng jiù néng zuò hǎo.", "Cách làm món này rất đơn giản, mười phút là nấu xong."),
                ("认真", "rènzhēn", "nghiêm túc, chăm chú", "她每次上课都听得非常认真。", "Tā měi cì shàngkè dōu tīng de fēicháng rènzhēn.", "Mỗi buổi lên lớp cô ấy đều nghe giảng vô cùng chăm chú."),
            ]),
        ],
    },
]

# 4 thửa cho HSK 4 Từ vựng (80 từ gắn bài ôn) + 40 từ mở rộng tra cứu = 120 từ HSK 4
HSK4_LANDS = [
    {
        "ten": "Sự nghiệp, phỏng vấn và công sở",
        "muc_tieu": "Làm chủ từ vựng HSK 4 về tuyển dụng, kinh nghiệm làm việc, thu nhập và hợp tác chuyên nghiệp",
        "nhom_ma": "gia_dinh_nghe_nghiep",
        "bai": [
            ("Ứng tuyển và phỏng vấn", [
                ("招聘", "zhāopìn", "tuyển dụng", "这家互联网公司正在招聘软件工程师。", "Zhè jiā hùliánwǎng gōngsī zhèngzài zhāopìn ruǎnjiàn gōngchéngshī.", "Công ty công nghệ này đang tuyển dụng kỹ sư phần mềm."),
                ("应聘", "yìngpìn", "ứng tuyển", "大学毕业后，她去一家外企应聘翻译。", "Dàxué bìyè hòu, tā qù yì jiā wàiqǐ yìngpìn fānyì.", "Sau khi tốt nghiệp đại học, cô ấy đến một công ty nước ngoài ứng tuyển vị trí biên dịch."),
                ("面试", "miànshì", "phỏng vấn", "明天的面试很重要，你要提前准备好材料。", "Míngtiān de miànshì hěn zhòngyào, nǐ yào tíqián zhǔnbèi hǎo cáiliào.", "Buổi phỏng vấn ngày mai rất quan trọng, bạn phải chuẩn bị sẵn tài liệu trước."),
                ("经验", "jīngyàn", "kinh nghiệm", "王老师有十多年的汉语教学经验。", "Wáng lǎoshī yǒu shí duō nián de Hànyǔ jiàoxué jīngyàn.", "Cô Vương có hơn mười năm kinh nghiệm giảng dạy tiếng Hán."),
                ("能力", "nénglì", "năng lực, khả năng", "这份工作能锻炼我们解决问题的能力。", "Zhè fèn gōngzuò néng duànliàn wǒmen jiějué wèntí de nénglì.", "Công việc này có thể rèn luyện năng lực giải quyết vấn đề của chúng ta."),
            ]),
            ("Trách nhiệm và tiến độ", [
                ("负责", "fùzé", "phụ trách, chịu trách nhiệm", "这次新产品的宣传活动由李经理负责。", "Zhè cì xīn chǎnpǐn de xuānchuán huódòng yóu Lǐ jīnglǐ fùzé.", "Hoạt động quảng bá sản phẩm mới lần này do giám đốc Lý phụ trách."),
                ("任务", "rènwu", "nhiệm vụ", "大家团结合作，提前完成了这项任务。", "Dàjiā tuánjié hézuò, tíqián wánchéng le zhè xiàng rènwu.", "Mọi người đoàn kết hợp tác, hoàn thành trước thời hạn nhiệm vụ này."),
                ("计划", "jìhuà", "kế hoạch; lên kế hoạch", "做事情以前最好先制定一个详细的计划。", "Zuò shìqing yǐqián zuì hǎo xiān zhìdìng yígè xiángxì de jìhuà.", "Trước khi làm việc tốt nhất hãy lập một kế hoạch chi tiết."),
                ("按时", "ànshí", "đúng giờ, đúng hạn", "不管是上班还是开会，他每次都按时到。", "Bùguǎn shì shàngbān háishi kāihuì, tā měi cì dōu ànshí dào.", "Dù là đi làm hay họp hành, lần nào anh ấy cũng đến đúng giờ."),
                ("加班", "jiābān", "làm thêm giờ, tăng ca", "最近项目比较忙，我们周末可能要加班。", "Zuìjìn xiàngmù bǐjiào máng, wǒmen zhōumò kěnéng yào jiābān.", "Gần đây dự án khá bận, cuối tuần chúng tôi có thể phải tăng ca."),
            ]),
            ("Đãi ngộ và phát triển", [
                ("工资", "gōngzī", "tiền lương", "虽然刚毕业工资不高，但能学到很多东西。", "Suīrán gāng bìyè gōngzī bù gāo, dàn néng xuédào hěn duō dōngxi.", "Tuy mới ra trường lương chưa cao, nhưng học hỏi được rất nhiều điều."),
                ("奖金", "jiǎngjīn", "tiền thưởng", "年底公司给表现优秀的员工发了奖金。", "Niándǐ gōngsī gěi biǎoxiàn yōuxiù de yuángōng fā le jiǎngjīn.", "Cuối năm công ty đã phát tiền thưởng cho nhân viên có biểu hiện xuất sắc."),
                ("专业", "zhuānyè", "chuyên ngành; chuyên nghiệp", "他在大学学的是国际贸易专业。", "Tā zài dàxué xué de shì guójì màoyì zhuānyè.", "Ở đại học anh ấy học chuyên ngành thương mại quốc tế."),
                ("成功", "chénggōng", "thành công", "失败是成功之母，不要轻易放弃。", "Shībài shì chénggōng zhī mǔ, búyào qīngyì fàngqì.", "Thất bại là mẹ thành công, đừng dễ dàng bỏ cuộc."),
                ("顺利", "shùnlì", "thuận lợi, suôn sẻ", "祝你这次出差一切顺利，早日回来！", "Zhù nǐ zhè cì chūchāi yíqiè shùnlì, zǎorì huílái!", "Chúc chuyến công tác lần này của bạn mọi bề thuận lợi, sớm trở về!"),
            ]),
            ("Giao dịch và hợp tác", [
                ("联系", "liánxì", "liên hệ, liên lạc", "到了上海以后，请马上发短信联系我。", "Dào le Shànghǎi yǐhòu, qǐng mǎshàng fā duǎnxìn liánxì wǒ.", "Sau khi tới Thượng Hải, hãy nhắn tin liên hệ với tôi ngay nhé."),
                ("讨论", "tǎolùn", "thảo luận", "大家正在会议室里讨论下个月的方案。", "Dàjiā zhèngzài huìyìshì lǐ tǎolùn xià gè yuè de fāng'àn.", "Mọi người đang ở trong phòng họp thảo luận phương án tháng sau."),
                ("总结", "zǒngjié", "tổng kết", "每学完一课，她都会认真总结语法重点。", "Měi xué wán yí kè, tā dōu huì rènzhēn zǒngjié yǔfǎ zhòngdiǎn.", "Mỗi khi học xong một bài, cô ấy đều tổng kết kỹ trọng điểm ngữ pháp."),
                ("提供", "tígōng", "cung cấp", "这家宾馆为客人提供免费的早餐。", "Zhè jiā bīnguǎn wèi kèrén tígōng miǎnfèi de zǎocān.", "Khách sạn này cung cấp bữa sáng miễn phí cho khách."),
                ("通知", "tōngzhī", "thông báo", "会议时间改到明天上午了，请通知大家。", "Huìyì shíjiān gǎi dào míngtiān shàngwǔ le, qǐng tōngzhī dàjiā.", "Giờ họp đã đổi sang sáng mai rồi, vui lòng thông báo cho mọi người."),
            ]),
        ],
    },
    {
        "ten": "Cảm xúc, tính cách và quan hệ xã hội",
        "muc_tieu": "Diễn đạt tinh tế thái độ, tính cách, sự khích lệ và mối quan hệ giữa người với người ở cấp HSK 4",
        "nhom_ma": "chao_hoi_giao_tiep",
        "bai": [
            ("Cảm xúc và tâm trạng", [
                ("感动", "gǎndòng", "cảm động", "这部电影里的故事让观众非常感动。", "Zhè bù diànyǐng lǐ de gùshi ràng guānzhòng fēicháng gǎndòng.", "Câu chuyện trong bộ phim này khiến khán giả vô cùng cảm động."),
                ("激动", "jīdòng", "xúc động, phấn khích", "收到大学录取通知书时，他激动得跳了起来。", "Shōudào dàxué lùqǔ tōngzhīshū shí, tā jīdòng de tiào le qǐlái.", "Khi nhận giấy báo trúng tuyển đại học, cậu ấy phấn khích nhảy cẫng lên."),
                ("后悔", "hòuhuǐ", "hối hận", "年轻时不努力学习，将来一定会后悔。", "Niánqīng shí bù nǔlì xuéxí, jiānglái yídìng huì hòuhuǐ.", "Lúc trẻ không chăm chỉ học tập, sau này nhất định sẽ hối hận."),
                ("羡慕", "xiànmù", "ngưỡng mộ", "大家都很羡慕她能说一口流利的汉语。", "Dàjiā dōu hěn xiànmù tā néng shuō yì kǒu liúlì de Hànyǔ.", "Mọi người đều rất ngưỡng mộ cô ấy nói tiếng Hán lưu loát."),
                ("愉快", "yúkuài", "vui vẻ, dễ chịu", "祝您和家人度过一个愉快的周末！", "Zhù nín hé jiārén dùguò yígè yúkuài de zhōumò!", "Chúc ngài và gia đình đón một kỳ nghỉ cuối tuần vui vẻ!"),
            ]),
            ("Tính cách và phẩm chất", [
                ("幽默", "yōumò", "hài hước, dí dỏm", "林老师说话很幽默，大家都喜欢上他的课。", "Lín lǎoshī shuōhuà hěn yōumò, dàjiā dōu xǐhuan shàng tā de kè.", "Thầy Lâm nói chuyện rất hài hước, ai cũng thích học giờ của thầy."),
                ("诚实", "chéngshí", "thành thật, trung thực", "诚实是人与人之间建立信任的基础。", "Chéngshí shì rén yǔ rén zhījiān jiànlì xìnrèn de jīchǔ.", "Trung thực là nền tảng xây dựng lòng tin giữa người với người."),
                ("耐心", "nàixīn", "kiên nhẫn", "护士非常有耐心地回答了病人的问题。", "Hùshi fēicháng yǒu nàixīn de huídá le bìngrén de wèntí.", "Cô y tá trả lời câu hỏi của bệnh nhân vô cùng kiên nhẫn."),
                ("勇敢", "yǒnggǎn", "dũng cảm", "遇到困难的时候，我们要勇敢地面对它。", "Yùdào kùnnan de shíhou, wǒmen yào yǒnggǎn de miànduì tā.", "Khi gặp khó khăn, chúng ta phải dũng cảm đối diện với nó."),
                ("骄傲", "jiāo'ào", "tự hào; kiêu ngạo", "取得好成绩也不要骄傲，还要继续努力。", "Qǔdé hǎo chéngjì yě búyào jiāo'ào, hái yào jìxù nǔlì.", "Đạt thành tích tốt cũng đừng kiêu ngạo, còn phải tiếp tục cố gắng."),
            ]),
            ("Giao tiếp và ứng xử", [
                ("尊重", "zūnzhòng", "tôn trọng", "我们应该尊重不同国家的文化和习惯。", "Wǒmen yīnggāi zūnzhòng bùtóng guójiā de wénhuà hé xíguàn.", "Chúng ta nên tôn trọng văn hóa và tập quán của các quốc gia khác nhau."),
                ("鼓励", "gǔlì", "khích lệ, động viên", "每当我失去信心时，父母都会鼓励我。", "Měi dāng wǒ shīqù xìnxīn shí, fùmǔ dōu huì gǔlì wǒ.", "Mỗi khi tôi mất tự tin, bố mẹ đều động viên khích lệ tôi."),
                ("批评", "pīpíng", "phê bình", "虚心接受别人的批评，才能进步得更快。", "Xūxīn jiēshòu biérén de pīpíng, cái néng jìnbù de gèng kuài.", "Khiêm tốn tiếp thu lời phê bình của người khác mới tiến bộ nhanh hơn."),
                ("原谅", "yuánliàng", "tha thứ", "既然他已经诚恳道歉了，你就原谅他吧。", "Jìrán tā yǐjīng chéngkěn dàoqiàn le, nǐ jiù yuánliàng tā ba.", "Đã là anh ấy thành khẩn xin lỗi rồi, bạn hãy tha thứ cho anh ấy nhé."),
                ("道歉", "dàoqiàn", "xin lỗi", "因为自己迟到了，他向大家表示道歉。", "Yīnwèi zìjǐ chídào le, tā xiàng dàjiā biǎoshì dàoqiàn.", "Vì bản thân đến muộn, anh ấy đã bày tỏ lời xin lỗi với mọi người."),
            ]),
            ("Quan hệ và ấn tượng", [
                ("印象", "yìnxiàng", "ấn tượng", "杭州美丽的西湖给我留下了深刻的印象。", "Hángzhōu měilì de Xīhú gěi wǒ liúxià le shēnkè de yìnxiàng.", "Tây Hồ tươi đẹp ở Hàng Châu để lại cho tôi ấn tượng sâu sắc."),
                ("信任", "xìnrèn", "tín nhiệm, tin cậy", "好朋友之间最重要的是互相理解和信任。", "Hǎo péngyou zhījiān zuì zhòngyào de shì hùxiāng lǐjiě hé xìnrèn.", "Giữa những người bạn tốt, điều quan trọng nhất là thấu hiểu và tin cậy lẫn nhau."),
                ("误会", "wùhuì", "hiểu lầm", "只要把事情解释清楚，就能消除误会。", "Zhǐyào bǎ shìqing jiěshì qīngchu, jiù néng xiāochú wùhuì.", "Chỉ cần giải thích rõ sự việc là có thể xóa bỏ hiểu lầm."),
                ("邀请", "yāoqǐng", "mời", "非常感谢您邀请我参加今天的晚会。", "Fēicháng gǎnxiè nín yāoqǐng wǒ cānjiā jīntiān de wǎnhuì.", "Vô cùng cảm ơn ngài đã mời tôi tham dự buổi dạ hội hôm nay."),
                ("友好", "yǒuhǎo", "thân thiện, hữu nghị", "这所学校的学生对留学生特别友好。", "Zhè suǒ xuéxiào de xuésheng duì liúxuéshēng tèbié yǒuhǎo.", "Sinh viên ngôi trường này đặc biệt thân thiện với lưu học sinh."),
            ]),
        ],
    },
    {
        "ten": "Học thuật, tư duy và liên từ lập luận",
        "muc_tieu": "Vận dụng từ vựng học thuật và các liên từ logic trọng tâm thường gặp trong Đọc – Viết HSK 4",
        "nhom_ma": "lien_tu_quan_he",
        "bai": [
            ("Học tập và nghiên cứu", [
                ("知识", "zhīshi", "kiến thức, tri thức", "多读书可以帮助我们丰富各方面的知识。", "Duō dúshū kěyǐ bāngzhù wǒmen fēngfù gè fāngmiàn de zhīshi.", "Đọc nhiều sách giúp chúng ta làm phong phú kiến thức mọi mặt."),
                ("阅读", "yuèdú", "đọc, đọc hiểu", "每天坚持阅读中文文章能扩大词汇量。", "Měitiān jiānchí yuèdú Zhōngwén wénzhāng néng kuòdà cíhuìliàng.", "Kiên trì đọc bài viết tiếng Trung mỗi ngày giúp mở rộng vốn từ."),
                ("翻译", "fānyì", "dịch thuật; phiên dịch viên", "请把这篇短文翻译成通顺的越南语。", "Qǐng bǎ zhè piān duǎnwén fānyì chéng tōngshùn de Yuènányǔ.", "Vui lòng dịch đoạn văn ngắn này sang tiếng Việt trôi chảy."),
                ("研究", "yánjiū", "nghiên cứu", "这位教授专门研究中国古代文学。", "Zhè wèi jiàoshòu zhuānmén yánjiū Zhōngguó gǔdài wénxué.", "Vị giáo sư này chuyên nghiên cứu văn học cổ đại Trung Quốc."),
                ("方法", "fāngfǎ", "phương pháp", "找到适合自己的学习方法比死记硬背更有效。", "Zhǎodào shìhé zìjǐ de xuéxí fāngfǎ bǐ sǐjì-yìngbèi gèng yǒuxiào.", "Tìm được phương pháp học phù hợp với mình hiệu quả hơn học vẹt."),
            ]),
            ("Phân tích và đánh giá", [
                ("原因", "yuányīn", "nguyên nhân", "警察正在调查这起交通事故的原因。", "Jǐngchá zhèngzài diàochá zhè qǐ jiāotōng shìgù de yuányīn.", "Cảnh sát đang điều tra nguyên nhân vụ tai nạn giao thông này."),
                ("结果", "jiéguǒ", "kết quả", "比赛结果已经出来了，我们班得了第一。", "Bǐsài jiéguǒ yǐjīng chūlái le, wǒmen bān dé le dì-yī.", "Kết quả cuộc thi đã có rồi, lớp chúng tôi giành giải nhất."),
                ("优点", "yōudiǎn", "ưu điểm", "每个人都有自己的优点，也有缺点。", "Měi gè rén dōu yǒu zìjǐ de yōudiǎn, yě yǒu quēdiǎn.", "Mỗi người đều có ưu điểm riêng và cũng có khuyết điểm."),
                ("缺点", "quēdiǎn", "khuyết điểm, nhược điểm", "做事情太马虎是他最大的缺点。", "Zuò shìqing tài mǎhu shì tā zuì dà de quēdiǎn.", "Làm việc quá qua loa đại khái là nhược điểm lớn nhất của anh ấy."),
                ("标准", "biāozhǔn", "tiêu chuẩn; chuẩn xác", "这位播音员的普通话发音非常标准。", "Zhè wèi bōyīnyuán de Pǔtōnghuà fāyīn fēicháng biāozhǔn.", "Phát âm tiếng Phổ thông của phát thanh viên này vô cùng chuẩn xác."),
            ]),
            ("Liên từ lập luận (1)", [
                ("尽管", "jǐnguǎn", "cho dù, mặc dù", "尽管外面下着大雨，他还是准时赶到了。", "Jǐnguǎn wàimiàn xiàzhe dàyǔ, tā háishi zhǔnshí gǎndào le.", "Mặc dù bên ngoài mưa to, anh ấy vẫn kịp tới đúng giờ."),
                ("不仅", "bùjǐn", "không những", "她不仅会说英语，而且汉语也说得很好。", "Tā bùjǐn huì shuō Yīngyǔ, érqiě Hànyǔ yě shuō de hěn hǎo.", "Cô ấy không những biết nói tiếng Anh mà tiếng Hán cũng nói rất giỏi."),
                ("因此", "yīncǐ", "vì vậy, do đó", "他平时经常锻炼，因此身体一直很健康。", "Tā píngshí jīngcháng duànliàn, yīncǐ shēntǐ yìzhí hěn jiànkāng.", "Thường ngày ông ấy hay tập luyện, do đó cơ thể luôn khỏe mạnh."),
                ("否则", "fǒuzé", "nếu không thì", "快点儿出门吧，否则就要赶不上飞机了。", "Kuàidiǎnr chūmén ba, fǒuzé jiù yào gǎnbushàng fēijī le.", "Mau ra khỏi nhà thôi, nếu không sẽ không kịp chuyến bay mất."),
                ("不管", "bùguǎn", "bất kể, cho dù", "不管遇到多大的困难，我们都不能放弃。", "Bùguǎn yùdào duō dà de kùnnan, wǒmen dōu bù néng fàngqì.", "Bất kể gặp khó khăn lớn đến đâu, chúng ta đều không được bỏ cuộc."),
            ]),
            ("Liên từ & phó từ lập luận (2)", [
                ("既然", "jìrán", "đã là, xét thấy", "既然大家都没意见，我们就按原计划办吧。", "Jìrán dàjiā dōu méi yìjiàn, wǒmen jiù àn yuán jìhuà bàn ba.", "Đã là mọi người đều không có ý kiến gì, ta cứ làm theo kế hoạch cũ nhé."),
                ("居然", "jūrán", "không ngờ lại", "这么难的数学题，弟弟居然十分钟就做出来了。", "Zhème nán de shùxué tí, dìdi jūrán shí fēnzhōng jiù zuò chūlái le.", "Bài toán khó thế này mà em trai không ngờ chỉ mười phút đã giải ra."),
                ("究竟", "jiūjìng", "rốt cuộc", "你究竟想去哪家公司，想清楚了吗？", "Nǐ jiūjìng xiǎng qù nǎ jiā gōngsī, xiǎng qīngchu le ma?", "Rốt cuộc bạn muốn vào công ty nào, đã nghĩ kỹ chưa?"),
                ("的确", "díquè", "quả thực, đích thực", "这家饭馆的烤鸭的确名不虚传，太好吃了。", "Zhè jiā fànguǎn de kǎoyā díquè míngbùxūchuán, tài hǎochī le.", "Món vịt quay của tiệm này quả thực danh bất hư truyền, ngon tuyệt."),
                ("恐怕", "kǒngpà", "e rằng, sợ là", "天这么阴，今天下午恐怕要下雪。", "Tiān zhème yīn, jīntiān xiàwǔ kǒngpà yào xiàxuě.", "Trời âm u thế này, chiều nay e rằng sẽ có tuyết rơi."),
            ]),
        ],
    },
    {
        "ten": "Đời sống hiện đại, du lịch và môi trường",
        "muc_tieu": "Sử dụng thành thạo từ vựng HSK 4 về tiêu dùng, giao thông hàng không, sức khỏe và bảo vệ môi trường",
        "nhom_ma": "vi_tri_phuong_huong",
        "bai": [
            ("Mua sắm và tiêu dùng", [
                ("质量", "zhìliàng", "chất lượng", "这个牌子的手机质量很好，价格也合理。", "Zhège páizi de shǒujī zhìliàng hěn hǎo, jiàgé yě hélǐ.", "Điện thoại hãng này chất lượng rất tốt, giá cả cũng hợp lý."),
                ("价格", "jiàgé", "giá cả", "节日期间，不少商场降低了商品的价格。", "Jiérì qījiān, bù shǎo shāngchǎng jiàngdī le shāngpǐn de jiàgé.", "Trong dịp lễ, không ít trung tâm thương mại giảm giá hàng hóa."),
                ("打折", "dǎzhé", "giảm giá, chiết khấu", "换季的时候，这家服装店全场五折起打折。", "Huànjì de shíhou, zhè jiā fúzhuāngdiàn quánchǎng wǔ zhé qǐ dǎzhé.", "Vào dịp giao mùa, tiệm quần áo này giảm giá toàn bộ từ 50%."),
                ("免费", "miǎnfèi", "miễn phí", "市博物馆每周二到周日对公众免费开放。", "Shì bówùguǎn měi zhōu'èr dào zhōurì duì gōngzhòng miǎnfèi kāifàng.", "Bảo tàng thành phố mở cửa miễn phí cho công chúng từ thứ Ba đến Chủ nhật."),
                ("顾客", "gùkè", "khách hàng", "服务员热情周到的态度赢得了顾客的好评。", "Fúwùyuán rèqíng zhōudào de tàidù yíngdé le gùkè de hǎopíng.", "Thái độ nhiệt tình chu đáo của nhân viên phục vụ nhận được lời khen của khách hàng."),
            ]),
            ("Hàng không và giao thông", [
                ("航班", "hángbān", "chuyến bay", "因为大雾，飞往北京的航班推迟了两个小时。", "Yīnwèi dàwù, fēi wǎng Běijīng de hángbān tuīchí le liǎng gè xiǎoshí.", "Do sương mù dày, chuyến bay đi Bắc Kinh bị hoãn hai tiếng đồng hồ."),
                ("推迟", "tuīchí", "hoãn lại, lùi lịch", "如果明天还下雨，运动会就推迟到下周举行。", "Rúguǒ míngtiān hái xiàyǔ, yùndònghuì jiù tuīchí dào xià zhōu jǔxíng.", "Nếu ngày mai vẫn mưa, hội thao sẽ lùi sang tuần sau tổ chức."),
                ("提前", "tíqián", "sớm hơn dự kiến, làm trước", "坐国际航班最好提前三个小时到机场。", "Zuò guójì hángbān zuì hǎo tíqián sān gè xiǎoshí dào jīchǎng.", "Đi chuyến bay quốc tế tốt nhất nên tới sân bay trước ba tiếng."),
                ("交通", "jiāotōng", "giao thông", "地铁开通以后，这一带的交通方便多了。", "Dìtiě kāitōng yǐhòu, zhè yídài de jiāotōng fāngbiàn duō le.", "Sau khi tàu điện ngầm thông tuyến, giao thông khu vực này thuận tiện hơn hẳn."),
                ("安全", "ānquán", "an toàn", "开车的时候一定要系好安全带，注意安全。", "Kāichē de shíhou yídìng yào jì hǎo ānquándài, zhùyì ānquán.", "Khi lái xe nhất định phải thắt dây an toàn, chú ý an toàn."),
            ]),
            ("Môi trường và thiên nhiên", [
                ("环境", "huánjìng", "môi trường", "这儿空气新鲜，周围的环境也非常优美。", "Zhèr kōngqì xīnxiān, zhōuwéi de huánjìng yě fēicháng yōuměi.", "Ở đây không khí trong lành, môi trường xung quanh cũng rất tươi đẹp."),
                ("保护", "bǎohù", "bảo vệ", "保护地球环境是我们每一个人的责任。", "Bǎohù dìqiú huánjìng shì wǒmen měi yígè rén de zérèn.", "Bảo vệ môi trường Trái Đất là trách nhiệm của mỗi người chúng ta."),
                ("污染", "wūrǎn", "ô nhiễm", "少开私家车、多坐公交车可以减少空气污染。", "Shǎo kāi sījiāchē, duō zuò gōngjiāochē kěyǐ jiǎnshǎo kōngqì wūrǎn.", "Ít đi xe riêng, đi xe buýt nhiều hơn có thể giảm ô nhiễm không khí."),
                ("节约", "jiéyuē", "tiết kiệm", "洗手以后请随手关紧水龙头，节约用水。", "Xǐshǒu yǐhòu qǐng suíshǒu guān jǐn shuǐlóngtóu, jiéyuē yòngshuǐ.", "Rửa tay xong hãy tiện tay khóa chặt vòi nước để tiết kiệm nước."),
                ("塑料袋", "sùliàodài", "túi ni-lông", "去超市买菜时，妈妈总是自己带布袋，不用塑料袋。", "Qù chāoshì mǎi cài shí, māma zǒng shì zìjǐ dài bùdài, bú yòng sùliàodài.", "Khi đi siêu thị mua thức ăn, mẹ luôn tự mang túi vải chứ không dùng túi ni-lông."),
            ]),
            ("Sức khỏe và lối sống", [
                ("压力", "yālì", "áp lực", "工作压力太大的时候，可以去户外散散步。", "Gōngzuò yālì tài dà de shíhou, kěyǐ qù hùwài sànsan bù.", "Khi áp lực công việc quá lớn, có thể ra ngoài trời đi dạo."),
                ("减肥", "jiǎnféi", "giảm cân", "健康的减肥方法是合理饮食加上坚持运动。", "Jiànkāng de jiǎnféi fāngfǎ shì hélǐ yǐnshí jiā shàng jiānchí yùndòng.", "Phương pháp giảm cân lành mạnh là ăn uống hợp lý kết hợp kiên trì vận động."),
                ("效果", "xiàoguǒ", "hiệu quả", "这种感冒药效果不错，吃了两天就好多了。", "Zhè zhǒng gǎnmàoyào xiàoguǒ búcuò, chī le liǎng tiān jiù hǎo duō le.", "Loại thuốc cảm này hiệu quả khá tốt, uống hai ngày là đỡ hẳn."),
                ("坚持", "jiānchí", "kiên trì", "学外语最怕半途而废，贵在每天坚持。", "Xué wàiyǔ zuì pà bàntú'érfèi, guì zài měitiān jiānchí.", "Học ngoại ngữ sợ nhất bỏ dở giữa chừng, quý ở chỗ kiên trì mỗi ngày."),
                ("养成", "yǎngchéng", "hình thành, rèn thành (thói quen)", "从小养成爱看书的好习惯对一生都有益。", "Cóngxiǎo yǎngchéng ài kànshū de hǎo xíguàn duì yìshēng dōu yǒuyì.", "Hình thành thói quen tốt ham đọc sách từ nhỏ có ích cho cả cuộc đời."),
            ]),
        ],
    },
]

# 40 từ HSK 4 mở rộng bổ sung cho Từ điển Tra cứu & Thẻ lật (tổng HSK 4 = 120 từ)
HSK4_EXTRA_WORDS = [
    ("安排", "ānpái", "sắp xếp, bố trí", "秘书已经把明天的日程安排好了。", "Mìshū yǐjīng bǎ míngtiān de rìchéng ānpái hǎo le.", "Thư ký đã sắp xếp xong lịch trình ngày mai rồi."),
    ("按照", "ànzhào", "theo, chiếu theo", "请大家按照顺序排队上车。", "Qǐng dàjiā ànzhào shùnxù páiduì shàngchē.", "Xin mọi người xếp hàng lên xe theo thứ tự."),
    ("包括", "bāokuò", "bao gồm", "房租每个月三千元，包括水费和电费。", "Fángzū měi gè yuè sānqiān yuán, bāokuò shuǐfèi hé diànfèi.", "Tiền thuê nhà mỗi tháng 3.000 tệ, bao gồm tiền nước và tiền điện."),
    ("保证", "bǎozhèng", "đảm bảo, cam đoan", "我向你保证，下次绝不再迟到了。", "Wǒ xiàng nǐ bǎozhèng, xià cì jué bú zài chídào le.", "Tôi cam đoan với bạn, lần sau tuyệt đối không đến muộn nữa."),
    ("报名", "bàomíng", "đăng ký, ghi danh", "想参加汉语演讲比赛的同学请今天报名。", "Xiǎng cānjiā Hànyǔ yǎnjiǎng bǐsài de tóngxué qǐng jīntiān bàomíng.", "Các bạn muốn tham gia cuộc thi hùng biện tiếng Hán xin đăng ký hôm nay."),
    ("毕业", "bìyè", "tốt nghiệp", "姐姐今年夏天从北京大学毕业。", "Jiějie jīnnián xiàtiān cóng Běijīng Dàxué bìyè.", "Chị gái mùa hè năm nay tốt nghiệp Đại học Bắc Kinh."),
    ("表扬", "biǎoyáng", "biểu dương, khen ngợi", "老师在全班同学面前表扬了他的进步。", "Lǎoshī zài quánbān tóngxué miànqián biǎoyáng le tā de jìnbù.", "Thầy giáo khen ngợi sự tiến bộ của cậu ấy trước cả lớp."),
    ("并且", "bìngqiě", "đồng thời, hơn nữa", "她做事情很快，并且质量也很高。", "Tā zuò shìqing hěn kuài, bìngqiě zhìliàng yě hěn gāo.", "Cô ấy làm việc rất nhanh, hơn nữa chất lượng cũng rất cao."),
    ("博士", "bóshì", "tiến sĩ", "他的哥哥正在读计算机专业的博士。", "Tā de gēge zhèngzài dú jìsuànjī zhuānyè de bóshì.", "Anh trai cậu ấy đang học tiến sĩ chuyên ngành máy tính."),
    ("差不多", "chàbuduō", "xấp xỉ, gần như nhau", "这两条裙子的颜色差不多，你更喜欢哪条？", "Zhè liǎng tiáo qúnzi de yánsè chàbuduō, nǐ gèng xǐhuan nǎ tiáo?", "Màu sắc của hai chiếc váy này gần giống nhau, bạn thích chiếc nào hơn?"),
    ("长城", "Chángchéng", "Vạn Lý Trường Thành", "不到长城非好汉，周末我们去爬长城吧。", "Bú dào Chángchéng fēi hǎohàn, zhōumò wǒmen qù pá Chángchéng ba.", "Bất đáo Trường Thành phi hảo hán, cuối tuần chúng mình đi leo Trường Thành nhé."),
    ("乘坐", "chéngzuò", "đi, đáp (phương tiện giao thông)", "欢迎各位旅客乘坐本次高速列车。", "Huānyíng gèwèi lǚkè chéngzuò běn cì gāosù lièchē.", "Chào mừng quý hành khách đi trên chuyến tàu cao tốc này."),
    ("吃惊", "chījīng", "kinh ngạc, ngạc nhiên", "听到这个消息，大家都感到非常吃惊。", "Tīngdào zhège xiāoxi, dàjiā dōu gǎndào fēicháng chījīng.", "Nghe được tin này, mọi người đều cảm thấy hết sức ngạc nhiên."),
    ("重新", "chóngxīn", "làm lại từ đầu", "刚才文件没保存好，只好重新写一遍。", "Gāngcái wénjiàn méi bǎocún hǎo, zhǐhǎo chóngxīn xiě yí biàn.", "Vừa nãy tệp chưa lưu kỹ, đành phải viết lại một lượt từ đầu."),
    ("出差", "chūchāi", "đi công tác", "爸爸下星期要去广州出差五天。", "Bàba xià xīngqī yào qù Guǎngzhōu chūchāi wǔ tiān.", "Tuần sau bố phải đi công tác Quảng Châu năm ngày."),
    ("出发", "chūfā", "xuất phát, khởi hành", "明天早上七点我们在学校大门口准时出发。", "Míngtiān zǎoshang qī diǎn wǒmen zài xuéxiào dàménkǒu zhǔnshí chūfā.", "Bảy giờ sáng mai chúng ta xuất phát đúng giờ ở cổng chính trường."),
    ("粗心", "cūxīn", "bất cẩn, cẩu thả", "考试时别太粗心，做完题要检查一遍。", "Kǎoshì shí bié tài cūxīn, zuò wán tí yào jiǎnchá yí biàn.", "Khi thi đừng quá bất cẩn, làm xong bài phải kiểm tra lại một lượt."),
    ("答案", "dá'àn", "đáp án", "请先自己思考，不要马上看后面的答案。", "Qǐng xiān zìjǐ sīkǎo, búyào mǎshàng kàn hòumiàn de dá'àn.", "Hãy tự suy nghĩ trước, đừng xem ngay đáp án phía sau."),
    ("打扮", "dǎban", "trang điểm, ăn diện", "今天去参加婚礼，她特意打扮了一番。", "Jīntiān qù cānjiā hūnlǐ, tā tèyì dǎban le yì fān.", "Hôm nay đi dự đám cưới, cô ấy đặc biệt sửa soạn trang điểm."),
    ("打扰", "dǎrǎo", "làm phiền", "对不起，这么晚还打电话打扰您休息。", "Duìbuqǐ, zhème wǎn hái dǎ diànhuà dǎrǎo nín xiūxi.", "Xin lỗi, muộn thế này còn gọi điện làm phiền ngài nghỉ ngơi."),
    ("导游", "dǎoyóu", "hướng dẫn viên du lịch", "这位导游对故宫的历史介绍得非常详细。", "Zhè wèi dǎoyóu duì Gùgōng de lìshǐ jièshào de fēicháng xiángxì.", "Vị hướng dẫn viên này giới thiệu lịch sử Cố Cung vô cùng chi tiết."),
    ("得意", "déyì", "đắc ý, hài lòng", "看到自己画的画儿得了奖，弟弟十分得意。", "Kàndào zìjǐ huà de huàr dé le jiǎng, dìdi shífēn déyì.", "Thấy bức tranh mình vẽ đoạt giải, em trai vô cùng đắc ý."),
    ("登机牌", "dēngjīpái", "thẻ lên máy bay", "请拿好您的护照和登机牌准备登机。", "Qǐng ná hǎo nín de hùzhào hé dēngjīpái zhǔnbèi dēngjī.", "Xin cầm sẵn hộ chiếu và thẻ lên máy bay của quý khách để chuẩn bị lên tàu bay."),
    ("调查", "diàochá", "điều tra, khảo sát", "公司对消费者的购买习惯做了一次调查。", "Gōngsī duì xiāofèizhě de gòumǎi xíguàn zuò le yí cì diàochá.", "Công ty đã thực hiện một cuộc khảo sát về thói quen mua hàng của người tiêu dùng."),
    ("对话", "duìhuà", "hội thoại, đối thoại", "请两个同学一组，练习课本上的这段对话。", "Qǐng liǎng gè tóngxué yì zǔ, liànxí kèběn shàng de zhè duàn duìhuà.", "Mời hai bạn một nhóm luyện tập đoạn hội thoại này trong sách giáo khoa."),
    ("对面", "duìmiàn", "đối diện", "图书馆对面就是学生食堂，吃饭很方便。", "Túshūguǎn duìmiàn jiù shì xuésheng shítáng, chīfàn hěn fāngbiàn.", "Đối diện thư viện chính là nhà ăn sinh viên, ăn uống rất tiện."),
    ("发展", "fāzhǎn", "phát triển", "近年来，中国的电子商务发展得非常快。", "Jìnnián lái, Zhōngguó de diànzǐ shāngwù fāzhǎn de fēicháng kuài.", "Những năm gần đây, thương mại điện tử của Trung Quốc phát triển rất nhanh."),
    ("法律", "fǎlǜ", "pháp luật", "每个公民都应该了解并遵守国家的法律。", "Měi gè gōngmín dōu yīnggāi liǎojiě bìng zūnshǒu guójiā de fǎlǜ.", "Mỗi công dân đều nên tìm hiểu và tuân thủ pháp luật của nhà nước."),
    ("反对", "fǎnduì", "phản đối", "这个提议很合理，没有人表示反对。", "Zhège tíyì hěn hélǐ, méiyǒu rén biǎoshì fǎnduì.", "Đề xuất này rất hợp lý, không ai bày tỏ sự phản đối."),
    ("丰富", "fēngfù", "phong phú, dồi dào", "参加社团活动让我的大学生活更加丰富。", "Cānjiā shètuán huódòng ràng wǒ de dàxué shēnghuó gèngjiā fēngfù.", "Tham gia hoạt động câu lạc bộ giúp đời sống đại học của tôi thêm phong phú."),
    ("风景", "fēngjǐng", "phong cảnh", "桂林山水甲天下，那里的风景美极了。", "Guìlín shānshuǐ jiǎ tiānxià, nàlǐ de fēngjǐng měi jíle.", "Non nước Quế Lâm đẹp nhất thiên hạ, phong cảnh nơi đó đẹp tuyệt vời."),
    ("改变", "gǎibiàn", "thay đổi", "那次旅行改变了他对生活的看法。", "Nà cì lǚxíng gǎibiàn le tā duì shēnghuó de kànfǎ.", "Chuyến du lịch lần đó đã thay đổi cách nhìn của anh ấy về cuộc sống."),
    ("感谢", "gǎnxiè", "cảm tạ, biết ơn", "衷心感谢老师这三年来对我的关心和帮助。", "Zhōngxīn gǎnxiè lǎoshī zhè sān nián lái duì wǒ de guānxīn hé bāngzhù.", "Chân thành cảm ơn sự quan tâm và giúp đỡ của thầy cô dành cho em suốt ba năm qua."),
    ("鼓励", "gǔlì", "khích lệ", "老师的鼓励让我更有信心学好汉语。", "Lǎoshī de gǔlì ràng wǒ gèng yǒu xìnxīn xué hǎo Hànyǔ.", "Sự khích lệ của thầy giáo giúp tôi tự tin hơn để học tốt tiếng Hán."),
    ("挂", "guà", "treo; cúp (điện thoại)", "墙上挂着一张我们全家的合影。", "Qiáng shàng guàzhe yì zhāng wǒmen quánjiā de héyǐng.", "Trên tường treo một tấm ảnh chụp chung cả gia đình chúng tôi."),
    ("关键", "guānjiàn", "then chốt, mấu chốt", "学好口语的关键是多听、多说、不怕错。", "Xué hǎo kǒuyǔ de guānjiàn shì duō tīng, duō shuō, bú pà cuò.", "Mấu chốt để học tốt khẩu ngữ là nghe nhiều, nói nhiều, không sợ sai."),
    ("观众", "guānzhòng", "khán giả", "演出结束时，台下的观众热烈地鼓掌。", "Yǎnchū jiéshù shí, táixià de guānzhòng rèliè de gǔzhǎng.", "Khi buổi diễn kết thúc, khán giả dưới khán đài vỗ tay nhiệt liệt."),
    ("管理", "guǎnlǐ", "quản lý", "他在大学学的是企业管理专业。", "Tā zài dàxué xué de shì qǐyè guǎnlǐ zhuānyè.", "Ở đại học anh ấy học chuyên ngành quản trị doanh nghiệp."),
    ("广告", "guǎnggào", "quảng cáo", "这则公益广告提醒大家要保护野生动物。", "Zhè zé gōngyì guǎnggào tíxǐng dàjiā yào bǎohù yěshēng dòngwù.", "Mẫu quảng cáo cộng đồng này nhắc nhở mọi người bảo vệ động vật hoang dã."),
    ("国际", "guójì", "quốc tế", "上海每年都会举办很多大型国际展览。", "Shànghǎi měinián dōu huì jǔbàn hěn duō dàxíng guójì zhǎnlǎn.", "Thượng Hải mỗi năm đều tổ chức nhiều triển lãm quốc tế quy mô lớn."),
    ("合适", "héshì", "phù hợp, vừa vặn", "这双运动鞋大小很合适，穿着特别舒服。", "Zhè shuāng yùndòngxié dàxiǎo hěn héshì, chuānzhe tèbié shūfu.", "Đôi giày thể thao này cỡ rất vừa, đi vào cực kỳ êm chân."),
]


def place(options: list[str], correct_index: int, slot: int) -> tuple[list[str], int]:
    right = options[correct_index]
    others = [o for i, o in enumerate(options) if i != correct_index]
    idx = slot % len(options)
    others.insert(idx, right)
    return others, idx


def mc(opts: list[str], answer: int) -> list[dict]:
    return [{"noi_dung": o, "la_dap_an_dung": i == answer} for i, o in enumerate(opts)]


def ensure_word(db, level: int, uid: int, han: str, py: str, nghia: str, vd_cau: str, vd_py: str, vd_nghia: str, stats: dict) -> int:
    row = db.execute(
        text("SELECT id, trang_thai, cap_do_id, vd_cau FROM tu_vung WHERE chu_han = :h AND pinyin = :p"),
        {"h": han, "p": py},
    ).mappings().first()
    if row:
        if not row["vd_cau"] and vd_cau:
            db.execute(
                text("UPDATE tu_vung SET vd_cau = :c, vd_pinyin = :py, vd_nghia = :n WHERE id = :id"),
                {"c": vd_cau, "py": vd_py, "n": vd_nghia, "id": row["id"]},
            )
            stats["updated_examples"] += 1
        if row["trang_thai"] != "xuat_ban":
            db.execute(text("UPDATE tu_vung SET trang_thai = 'xuat_ban' WHERE id = :id"), {"id": row["id"]})
        return int(row["id"])
    res = db.execute(
        text("""
            INSERT INTO tu_vung (chu_han, pinyin, nghia, cap_do_id, vd_cau, vd_pinyin, vd_nghia, trang_thai, nguoi_tao_id)
            VALUES (:h, :p, :n, :c, :vc, :vp, :vn, 'xuat_ban', :u)
        """),
        {"h": han, "p": py, "n": nghia, "c": level, "vc": vd_cau, "vp": vd_py, "vn": vd_nghia, "u": uid},
    )
    stats["created_words"] += 1
    return int(res.lastrowid)


def seed_vocab_land(db, uid: int, level: int, land: dict, nhom_map: dict, stats: dict) -> None:
    exists = db.execute(
        text("SELECT 1 FROM bo_de WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = 'tu_vung' AND ten = :t LIMIT 1"),
        {"c": level, "t": land["ten"]},
    ).first()
    if exists:
        print(f"· Bỏ qua Từ vựng HSK {level} · {land['ten']} (đã có)")
        return

    nhom_id = nhom_map.get(land["nhom_ma"])
    groups = []
    for lesson_name, words in land["bai"]:
        w_items = []
        for han, py, nghia, vc, vp, vn in words:
            wid = ensure_word(db, level, uid, han, py, nghia, vc, vp, vn, stats)
            w_items.append((wid, han, py, nghia, vc, vp, vn))
        groups.append((lesson_name, w_items))
    db.commit()

    num_opts = 4 if level >= 4 else 3
    base = {
        "dang": "chon_mot",
        "cap_do_id": level,
        "ky_nang": "tu_vung",
        "dung_on_luyen": True,
        "dung_thi_thu": False,
        "nguon_noi_dung": "tu_soan",
        "nhom_kien_thuc_id": nhom_id,
    }

    flat = [w for _, ws in groups for w in ws]
    lessons_qids = []
    slot_counter = 0

    for g_idx, (lesson_name, ws) in enumerate(groups):
        qids = []
        for i, (wid, han, py, nghia, vc, vp, vn) in enumerate(ws):
            distractors = [ws[(i + 1) % 5][3], ws[(i + 2) % 5][3]]
            if num_opts == 4:
                distractors.append(flat[(g_idx * 5 + i + 7) % len(flat)][3])
            opts, ans = place([nghia] + distractors, 0, slot_counter)
            slot_counter += 1

            # Câu lẻ hỏi nghĩa trực tiếp của từ, câu chẵn hỏi nghĩa của từ đặt trong câu ngữ cảnh thực tế
            if i % 2 == 0:
                stem = han if level == 4 else f"{han}"
                pinyin_field = py
            else:
                stem = f"Trong câu “{vc}”, từ “{han}” có nghĩa phù hợp nhất là gì?"
                pinyin_field = f"{py} — {vp}"

            qid = create_question(db, QuestionIn(
                **base,
                tu_vung_id=wid,
                noi_dung=stem,
                pinyin=pinyin_field,
                dich_nghia=f"{han} ({py}): {nghia}\nVí dụ: {vc} ({vn})",
                goi_y=f"Chú ý cách đọc Pinyin “{py}” và ngữ cảnh sử dụng thường gặp của từ {han}.",
                goi_y_2=f"Thử đặt từ “{han}” vào câu ví dụ: “{vc}” để suy ra nghĩa tiếng Việt chính xác.",
                giai_thich=f"“{han}” ({py}) có nghĩa là “{nghia}”. Ví dụ: {vc} ({vn})",
                phuong_an=mc(opts, ans),
            ), uid)
            publish_question(db, qid, uid)
            qids.append(qid)
            stats["created_questions"] += 1
        lessons_qids.append((lesson_name, qids))

    # 10 câu Kiểm tra cuối thửa: kết hợp điền từ vào chỗ trống câu tiếng Trung & chọn từ theo nghĩa
    final_qids = []
    pick_indices = [0, 2, 4, 6, 8, 11, 13, 15, 17, 19]
    for k, idx in enumerate(pick_indices):
        wid, han, py, nghia, vc, vp, vn = flat[idx]
        d1 = flat[(idx + 5) % 20]
        d2 = flat[(idx + 11) % 20]
        raw_opts = [
            f"{han}" if level == 4 else f"{han} [{py}]",
            f"{d1[1]}" if level == 4 else f"{d1[1]} [{d1[2]}]",
            f"{d2[1]}" if level == 4 else f"{d2[1]} [{d2[2]}]",
        ]
        if num_opts == 4:
            d3 = flat[(idx + 16) % 20]
            raw_opts.append(f"{d3[1]}" if level == 4 else f"{d3[1]} [{d3[2]}]")
        opts, ans = place(raw_opts, 0, k + 1)

        if han in vc:
            blanked = vc.replace(han, "（　　）", 1)
            stem = f"Chọn từ thích hợp điền vào chỗ trống:\n{blanked}"
        else:
            stem = f"Từ tiếng Trung nào mang nghĩa “{nghia}”?"

        qid = create_question(db, QuestionIn(
            **base,
            tu_vung_id=wid,
            noi_dung=stem,
            pinyin=vp,
            dich_nghia=f"Câu hoàn chỉnh: {vc}\nDịch nghĩa: {vn}",
            goi_y=f"Nghĩa tiếng Việt của câu cần diễn đạt ý: “{vn}”.",
            goi_y_2=f"Cần tìm từ mang nghĩa “{nghia}” (phiên âm {py}) để hoàn chỉnh ngữ nghĩa của câu.",
            giai_thich=f"Đáp án đúng là {han} ({py}: {nghia}). Câu đầy đủ: {vc} ({vn})",
            phuong_an=mc(opts, ans),
        ), uid)
        publish_question(db, qid, uid)
        final_qids.append(qid)
        stats["created_questions"] += 1

    land_id = path_service.create_land(
        db,
        SimpleNamespace(cap_do_id=level, ky_nang="tu_vung", ten=land["ten"], muc_tieu=land["muc_tieu"]),
        uid,
    )
    for pos, (lname, qids) in enumerate(lessons_qids + [("Kiểm tra cuối thửa", final_qids)], start=1):
        lesson_id = path_service.create_lesson(
            db,
            SimpleNamespace(thua_id=land_id, vi_tri=pos, ten=lname, muc_tieu=None, tai_lieu_id=None),
            uid,
        )
        path_service.set_lesson_items(db, lesson_id, [SimpleNamespace(cau_hoi_id=q) for q in qids])
        path_service.lesson_status(db, lesson_id, "dang")
    path_service.land_status(db, land_id, "dang")
    stats["created_lands"] += 1
    print(f"→ Đã đăng Từ vựng HSK {level} · {land['ten']} (4 bài + 1 cuối thửa = 30 câu)")


def main() -> int:
    db = SessionLocal()
    stats = {"created_words": 0, "updated_examples": 0, "created_questions": 0, "created_lands": 0}
    try:
        uid = db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one()
        levels = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}
        nhom_map = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM nhom_kien_thuc")).all()}

        # 1. Bổ sung ví dụ cho các từ HSK 3 hiện có nếu đang trống
        for han, (vc, vp, vn) in HSK3_EXISTING_EXAMPLES.items():
            res = db.execute(
                text("UPDATE tu_vung SET vd_cau = :vc, vd_pinyin = :vp, vd_nghia = :vn WHERE cap_do_id = :c AND chu_han = :h AND (vd_cau IS NULL OR vd_cau = '')"),
                {"vc": vc, "vp": vp, "vn": vn, "c": levels["HSK3"], "h": han},
            )
            stats["updated_examples"] += int(res.rowcount or 0)
        db.commit()

        # 2. Nạp 2 thửa mới cho HSK 3 Từ vựng
        for land in HSK3_NEW_LANDS:
            seed_vocab_land(db, uid, levels["HSK3"], land, nhom_map, stats)

        # 3. Nạp 4 thửa cho HSK 4 Từ vựng (80 từ + 120 câu)
        for land in HSK4_LANDS:
            seed_vocab_land(db, uid, levels["HSK4"], land, nhom_map, stats)

        # 4. Nạp thêm 40 từ HSK 4 tra cứu mở rộng
        for han, py, nghia, vc, vp, vn in HSK4_EXTRA_WORDS:
            ensure_word(db, levels["HSK4"], uid, han, py, nghia, vc, vp, vn, stats)
        db.commit()

        print(f"HOÀN TẤT TỪ VỰNG: +{stats['created_words']} từ mới, +{stats['updated_examples']} ví dụ bổ sung, "
              f"+{stats['created_lands']} thửa, +{stats['created_questions']} câu ôn luyện.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
