"""Nạp danh mục Nhóm kiến thức và Ngân hàng câu hỏi Đánh giá đầu vào 8 câu (HSK 1–4).

- Chạy an toàn nhiều lần (idempotent): không tạo trùng câu hỏi nếu đã nạp.
- Kiểm tra tệp âm thanh vật lý trên ổ đĩa (`backend/uploads/`) trước khi bật `dung_dau_vao = 1` và `da_kiem_tra_audio = 1` cho câu Nghe.
- Bổ sung đầy đủ câu Dịch (`dich_cau` HSK 1–4) cho Câu 7 và câu Sắp xếp (`sap_xep` HSK 1–2) cho Câu 8.
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database.root_id import next_root_id
from app.database.session import SessionLocal
from app.storage.static_media import UPLOADS_DIR

NHOM_KIEN_THUC = [
    ("chao_hoi_giao_tiep", "Chào hỏi và giao tiếp cơ bản", "Lời chào, cảm ơn, xin lỗi, giới thiệu tên và quốc tịch"),
    ("gia_dinh_nghe_nghiep", "Gia đình và nghề nghiệp", "Đại từ nhân xưng, thành viên gia đình, nghề nghiệp cơ bản"),
    ("so_dem_luong_tu", "Số đếm và lượng từ", "Số đếm, lượng từ phổ biến (个, 本, 杯, 件, 张, 条...)"),
    ("thoi_gian_lich_hen", "Thời gian và lịch hẹn", "Giờ giấc, thứ ngày tháng năm, mốc thời gian và đổi lịch hẹn"),
    ("vi_tri_phuong_huong", "Vị trí và phương hướng", "Từ chỉ vị trí (上, 下, 里, 前, 后), động từ 在, đi lại"),
    ("phu_dinh_nghi_van", "Phủ định và câu hỏi", "Phân biệt 不 / 没 / 别, đại từ nghi vấn (什么, 谁, 哪儿, 怎么, 多少, 几)"),
    ("tro_tu_dong_thai", "Trợ từ động thái 了 / 过 / 着", "Biểu thị hành động hoàn thành, kinh nghiệm đã từng, trạng thái tiếp diễn"),
    ("bo_ngu", "Bổ ngữ kết quả, xu hướng, khả năng", "Bổ ngữ kết quả (完, 懂, 见), bổ ngữ xu hướng, bổ ngữ mức độ 得"),
    ("cau_so_sanh_nhan_manh", "Câu so sánh và câu chữ 把 / 被", "So sánh với 比 / 没有 / 一样, cấu trúc câu chữ 把 và câu bị động 被"),
    ("lien_tu_quan_he", "Liên từ đối lập, nhân quả, giả thiết", "虽然…但是, 因为…所以, 如果…就, 不仅…而且, 无论…都"),
]

TOPIC_PATTERNS = [
    ("lien_tu_quan_he", re.compile(r"虽然|但是|因为|所以|如果|不仅|而且|无论|既然|尽管")),
    ("cau_so_sanh_nhan_manh", re.compile(r"比|把|被|一样")),
    ("tro_tu_dong_thai", re.compile(r"过|着|了")),
    ("bo_ngu", re.compile(r"完|懂|清楚|起来|出去|进来|回去|得")),
    ("thoi_gian_lich_hen", re.compile(r"点|分|月|号|日|星期|周|今天|明天|昨天|上午|下午|晚上|年|时候")),
    ("vi_tri_phuong_huong", re.compile(r"上|下|里|外|前|后|左|右|旁边|中间|北|南|东|西|在")),
    ("phu_dinh_nghi_van", re.compile(r"什么|谁|哪|怎么|多少|几|为什么|不|没|别")),
    ("so_dem_luong_tu", re.compile(r"个|本|杯|件|张|条|岁|块|双|只|次")),
    ("gia_dinh_nghe_nghiep", re.compile(r"爸爸|妈妈|哥哥|姐姐|弟弟|妹妹|老师|医生|学生|朋友|同学|丈夫|妻子")),
]

DICH_CAU_SEED = [
    # HSK 1
    ("HSK1", "thoi_gian_lich_hen", "明天 上午 八 点 我们 见。", "míngtiān shàngwǔ bā diǎn wǒmen jiàn .",
     "Sáng mai 8 giờ chúng ta gặp nhau.",
     "Đạt đủ 3 ý: thời gian (sáng mai 8 giờ), chủ ngữ (chúng ta/chúng mình), hành động (gặp nhau).",
     "Trong tiếng Trung, trạng ngữ thời gian (明天上午八点) đặt trước hoặc ngay sau chủ ngữ, trước động từ (见).",
     ["8 giờ sáng mai chúng ta gặp nhau", "Sáng ngày mai lúc 8 giờ chúng mình gặp nhau"]),
    ("HSK1", "gia_dinh_nghe_nghiep", "我 姐姐 在 医院 工作。", "wǒ jiějie zài yīyuàn gōngzuò .",
     "Chị gái tôi làm việc ở bệnh viện.",
     "Đạt đủ 3 ý: chủ ngữ (chị gái tôi), nơi chốn (ở bệnh viện), động từ (làm việc).",
     "Cấu trúc 在 + địa điểm + động từ (在医院工作 = làm việc tại bệnh viện).",
     ["Chị tôi làm việc tại bệnh viện", "Chị gái của tôi đi làm ở bệnh viện"]),
    ("HSK1", "phu_dinh_nghi_van", "这 个 汉字 怎么 读？", "zhè ge hànzì zěnme dú ?",
     "Chữ Hán này đọc thế nào?",
     "Đạt đủ ý đối tượng (chữ Hán này) và câu hỏi cách thức (đọc như thế nào / đọc sao).",
     "怎么 + động từ dùng để hỏi cách thực hiện hành động (怎么读 = đọc thế nào).",
     ["Chữ Hán này đọc như thế nào", "Chữ tiếng Trung này đọc ra sao"]),
    ("HSK1", "so_dem_luong_tu", "桌子上 有 三 本 汉语 书。", "zhuōzishàng yǒu sān běn hànyǔ shū .",
     "Trên bàn có ba quyển sách tiếng Trung.",
     "Đạt đủ vị trí (trên bàn), số lượng (ba quyển/cuốn) và danh từ (sách tiếng Trung/tiếng Hán).",
     "Lượng từ của sách là 本 (běn); cấu trúc Vị trí + 有 + Số lượng + Danh từ.",
     ["Ở trên bàn có 3 cuốn sách tiếng Hán", "Trên cái bàn có ba quyển sách tiếng Trung"]),
    # HSK 2
    ("HSK2", "tro_tu_dong_thai", "我 去 过 两 次 北京。", "wǒ qù guo liǎng cì Běijīng .",
     "Tôi đã từng đi Bắc Kinh hai lần.",
     "Dịch rõ trợ từ kinh nghiệm 过 (đã từng) và bổ ngữ tần suất 两次 (hai lần) tới Bắc Kinh.",
     "Động từ + 过 biểu thị trải nghiệm đã từng xảy ra trong quá khứ.",
     ["Tôi từng đến Bắc Kinh 2 lần", "Mình đã đi Bắc Kinh hai lần rồi"]),
    ("HSK2", "cau_so_sanh_nhan_manh", "今天 的 天气 比 昨天 冷 一点儿。", "jīntiān de tiānqì bǐ zuótiān lěng yìdiǎnr .",
     "Thời tiết hôm nay lạnh hơn hôm qua một chút.",
     "Dịch đúng cấu trúc so sánh hơn (hôm nay so với hôm qua) và mức độ (lạnh hơn một chút).",
     "A 比 B + tính từ + 一点儿 biểu thị A hơn B một chút.",
     ["Hôm nay trời lạnh hơn hôm qua một chút", "Thời tiết ngày hôm nay hơi lạnh hơn ngày hôm qua"]),
    ("HSK2", "bo_ngu", "你 听 懂 老师 说 的 话 了 吗？", "nǐ tīng dǒng lǎoshī shuō de huà le ma ?",
     "Bạn đã nghe hiểu lời thầy giáo nói chưa?",
     "Dịch đúng bổ ngữ kết quả 听懂 (nghe hiểu) và cụm định ngữ 老师说的话 (lời thầy/cô giáo nói).",
     "听懂 là động từ + bổ ngữ kết quả (nghe và hiểu được).",
     ["Cậu nghe hiểu những gì cô giáo nói chưa", "Bạn có nghe hiểu lời giáo viên nói không"]),
    ("HSK2", "thoi_gian_lich_hen", "从 我 家 到 机场 要 一 个 小时。", "cóng wǒ jiā dào jīchǎng yào yí ge xiǎoshí .",
     "Từ nhà tôi đến sân bay mất một tiếng đồng hồ.",
     "Đạt đủ cấu trúc 从…到… (từ nhà tôi tới sân bay) và thời lượng (mất/cần 1 giờ/tiếng).",
     "从 A 到 B biểu thị khoảng cách từ điểm A đến điểm B; 要 biểu thị thời gian cần thiết.",
     ["Đi từ nhà tôi ra sân bay mất 1 giờ", "Từ nhà mình tới sân bay tốn một tiếng"]),
    # HSK 3
    ("HSK3", "cau_so_sanh_nhan_manh", "请 把 桌子上 的 笔记本电脑 拿 给 我。", "qǐng bǎ zhuōzishàng de bǐjìběndiànnǎo ná gěi wǒ .",
     "Xin hãy lấy chiếc máy tính xách tay trên bàn đưa cho tôi.",
     "Dịch đúng câu chữ 把: đối tượng xác định (máy tính xách tay/laptop trên bàn) và hành động (lấy đưa cho tôi).",
     "Câu chữ 把 đưa tân ngữ xác định lên trước động từ: 把 + Tân ngữ + Động từ + Thành phần khác.",
     ["Làm ơn đưa giúp tôi cái laptop ở trên bàn", "Hãy cầm chiếc máy tính xách tay trên bàn đưa cho tôi"]),
    ("HSK3", "lien_tu_quan_he", "虽然 下 着 大 雨，但是 他 还是 准时 到 了。", "suīrán xià zhe dà yǔ , dànshì tā háishi zhǔnshí dào le .",
     "Mặc dù trời đang mưa to nhưng anh ấy vẫn đến đúng giờ.",
     "Dịch đủ cặp quan hệ nhượng bộ Mặc dù... nhưng..., trạng thái mưa to và kết quả vẫn đến đúng giờ.",
     "Cấu trúc 虽然…但是… kết hợp phó từ 还是 nhấn mạnh sự việc không đổi dù có trở ngại.",
     ["Tuy trời mưa lớn nhưng anh ấy vẫn tới đúng giờ", "Dù đang mưa to, anh ấy vẫn đến đúng giờ"]),
    ("HSK3", "bo_ngu", "他 汉语 说 得 越 来 越 流利 了。", "tā hànyǔ shuō de yuè lái yuè liúlì le .",
     "Anh ấy nói tiếng Trung ngày càng lưu loát.",
     "Dịch đúng bổ ngữ mức độ 说得… và cấu trúc 越来越… (càng ngày càng trôi chảy/lưu loát).",
     "Động từ + 得 + 越来越 + Tính từ diễn tả mức độ tăng dần theo thời gian.",
     ["Tiếng Trung của anh ấy nói càng ngày càng trôi chảy", "Anh ấy nói tiếng Hán ngày một lưu loát hơn"]),
    ("HSK3", "tro_tu_dong_thai", "会议 室 的 门 开 着，里面 没 有 人。", "huìyì shì de mén kāi zhe , lǐmiàn méi yǒu rén .",
     "Cửa phòng họp đang mở, bên trong không có ai.",
     "Dịch đúng trạng thái tĩnh 开着 (đang mở) và mệnh đề sau (bên trong không có người).",
     "Động từ + 着 biểu thị sự duy trì của trạng thái (门开着 = cửa đang để mở).",
     ["Cửa phòng họp mở nhưng ở trong không có người", "Cửa của phòng họp đang mở, bên trong chẳng có ai"]),
    # HSK 4
    ("HSK4", "lien_tu_quan_he", "无论 遇到 多 大 的 困难，我们 都 不 应该 放弃。", "wúlùn yùdào duō dà de kùnnan , wǒmen dōu bù yīnggāi fàngqì .",
     "Cho dù gặp phải khó khăn lớn đến đâu, chúng ta cũng không nên từ bỏ.",
     "Dịch đúng cấu trúc điều kiện bất kể 无论…都… (bất luận/dù gặp khó khăn lớn thế nào) và kết luận (không nên bỏ cuộc/từ bỏ).",
     "无论…都… đi với từ nghi vấn phiếm chỉ (多大) diễn tả kết quả không đổi trong mọi tình huống.",
     ["Bất kể gặp khó khăn lớn thế nào chúng ta đều không nên bỏ cuộc", "Dù gặp khó khăn lớn tới đâu mình cũng không được từ bỏ"]),
    ("HSK4", "cau_so_sanh_nhan_manh", "那 本 小说 已经被 翻译 成 十 几 种 语言 了。", "nà běn xiǎoshuō yǐjīng bèi fānyì chéng shí jǐ zhǒng yǔyán le .",
     "Cuốn tiểu thuyết đó đã được dịch sang hơn mười thứ tiếng rồi.",
     "Dịch đúng thể bị động 被翻译成 (đã được dịch thành/sang) và số ước lượng 十几种语言 (hơn mười ngôn ngữ/thứ tiếng).",
     "被 + Động từ + 成 biểu thị đối tượng được biến đổi/chuyển dịch sang trạng thái hay ngôn ngữ khác.",
     ["Quyển tiểu thuyết kia đã được dịch ra mười mấy ngôn ngữ rồi", "Cuốn tiểu thuyết ấy đã được dịch sang hơn chục thứ tiếng"]),
    ("HSK4", "lien_tu_quan_he", "养成 良好 的 阅读 习惯 不仅 能 丰富 知识，而且 有助于 提高 写作 能力。",
     "yǎngchéng liánghǎo de yuèdú xíguàn bùjǐn néng fēngfù zhīshi , érqiě yǒuzhùyú tígāo xiězuò nénglì .",
     "Hình thành thói quen đọc sách tốt không những làm phong phú kiến thức mà còn giúp nâng cao khả năng viết.",
     "Dịch đủ chủ ngữ (rèn luyện/hình thành thói quen đọc tốt) và cặp tăng tiến 不仅…而且… (mở rộng kiến thức + giúp cải thiện kỹ năng viết).",
     "不仅…而且… nối hai vế tăng tiến; 有助于 mang nghĩa có ích/giúp ích cho việc gì.",
     ["Rèn thói quen đọc sách tốt không chỉ mở rộng kiến thức mà còn giúp cải thiện kỹ năng viết"]),
    ("HSK4", "bo_ngu", "做 任何 决定 之前，你 最好 先 把 情况 了解 清楚。", "zuò rènhé juédìng zhīqián , nǐ zuìhǎo xiān bǎ qíngkuàng liǎojiě qīngchu .",
     "Trước khi đưa ra bất kỳ quyết định nào, tốt nhất bạn nên tìm hiểu rõ tình hình trước.",
     "Dịch đủ mốc thời gian (trước khi đưa ra bất cứ quyết định nào), lời khuyên 最好 (tốt nhất nên) và 了解清楚 (tìm hiểu rõ tình hình).",
     "……之前 (trước khi...); 最好 (tốt nhất nên); 把 + Tân ngữ + Động từ + Bổ ngữ kết quả (了解清楚).",
     ["Trước khi quyết định bất cứ việc gì, tốt nhất bạn hãy nắm rõ tình hình trước"]),
]

SAP_XEP_HSK12_SEED = [
    # HSK 1 (Câu 8 nhánh HSK 1)
    ("HSK1", "thoi_gian_lich_hen", "Chiều nay bạn đi đâu?", ["今天", "下午", "你", "去", "哪儿"], ["今天下午你去哪儿"]),
    ("HSK1", "gia_dinh_nghe_nghiep", "Bố tôi là bác sĩ ở bệnh viện.", ["我", "爸爸", "是", "医院", "的", "医生"], ["我爸爸是医院的医生"]),
    ("HSK1", "so_dem_luong_tu", "Tôi muốn mua hai cốc trà nóng.", ["我", "想", "买", "两", "杯", "热茶"], ["我想买两杯热茶"]),
    ("HSK1", "vi_tri_phuong_huong", "Con mèo nhỏ ở dưới cái ghế.", ["小猫", "在", "椅子", "下面"], ["小猫在椅子下面"]),
    # HSK 2 (Câu 8 nhánh HSK 2)
    ("HSK2", "thoi_gian_lich_hen", "Mỗi sáng tôi đều chạy bộ nửa tiếng.", ["我", "每天", "早上", "都", "跑步", "半个小时"], ["我每天早上都跑步半个小时"]),
    ("HSK2", "cau_so_sanh_nhan_manh", "Dưa hấu hôm nay ngọt hơn hôm qua.", ["今天", "的", "西瓜", "比", "昨天", "甜"], ["今天的西瓜比昨天甜"]),
    ("HSK2", "tro_tu_dong_thai", "Tôi chưa từng xem bộ phim Trung Quốc này.", ["我", "没", "看", "过", "这个", "中国电影"], ["我没看过这个中国电影"]),
    ("HSK2", "bo_ngu", "Bài tập hôm nay tôi đã làm xong rồi.", ["今天", "的", "作业", "我", "做完", "了"], ["今天的作业我做完了"]),
]


def _infer_topic_code(text_blob: str) -> str:
    for code, pat in TOPIC_PATTERNS:
        if pat.search(text_blob):
            return code
    return "chao_hoi_giao_tiep"


def main() -> None:
    db = SessionLocal()
    try:
        # 1. Nạp 10 nhóm kiến thức chuẩn
        for ma, ten, mo_ta in NHOM_KIEN_THUC:
            db.execute(
                text("""
                    INSERT INTO nhom_kien_thuc (ma, ten, mo_ta, trang_thai)
                    VALUES (:ma, :ten, :mt, 'hoat_dong')
                    ON DUPLICATE KEY UPDATE ten = VALUES(ten), mo_ta = VALUES(mo_ta)
                """),
                {"ma": ma, "ten": ten, "mt": mo_ta},
            )
        topic_ids = {
            r["ma"]: int(r["id"])
            for r in db.execute(text("SELECT id, ma FROM nhom_kien_thuc")).mappings().all()
        }
        cap_ids = {
            r["ma"]: int(r["id"])
            for r in db.execute(text("SELECT id, ma FROM cap_do")).mappings().all()
        }

        # 2. Thực thi Phần 1 (bù khoi_tao cho tài khoản thiếu) & Phần 4 (tắt dung_on_luyen câu Nghe thiếu tep_audio riêng)
        db.execute(text("""
            INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong, tao_luc)
            SELECT n.id, 'khoi_tao', n.nang_luong, n.tao_luc
            FROM nguoi_dung n
            WHERE n.nang_luong > 0
              AND NOT EXISTS (SELECT 1 FROM nhat_ky_thuong t WHERE t.nguoi_dung_id = n.id AND t.ly_do = 'khoi_tao')
        """))
        db.execute(text("""
            UPDATE cau_hoi q
            SET q.dung_on_luyen = 0
            WHERE q.ky_nang = 'nghe'
              AND q.tep_audio IS NULL
              AND q.dung_thi_thu = 1
              AND NOT EXISTS (
                SELECT 1 FROM bo_de_cau_hoi i JOIN bo_de b ON b.id = i.bo_de_id
                WHERE i.cau_hoi_id = q.id AND b.loai IN ('bai', 'cuoi_thua')
              )
        """))

        # 3. Gắn nhom_kien_thuc_id cho các câu hỏi hiện có chưa được gắn nhóm
        untagged = db.execute(
            text("""
                SELECT id, dang, COALESCE(noi_dung, '') AS noi_dung, COALESCE(loi_nghe, '') AS loi_nghe
                FROM cau_hoi
                WHERE dang <> 'ngu_lieu' AND nhom_kien_thuc_id IS NULL
            """)
        ).mappings().all()
        for r in untagged:
            code = _infer_topic_code(f"{r['noi_dung']} {r['loi_nghe']}")
            db.execute(
                text("UPDATE cau_hoi SET nhom_kien_thuc_id = :nid WHERE id = :id"),
                {"nid": topic_ids[code], "id": r["id"]},
            )

        # 4. Bật dung_dau_vao = 1 cho các câu khách quan chất lượng cao đang có sẵn trong ngân hàng HSK 1–4
        for cap_ma, cap_id in cap_ids.items():
            # Từ vựng (chon_mot)
            tv_ids = db.execute(
                text("""
                    SELECT id FROM cau_hoi
                    WHERE cap_do_id = :c AND ky_nang = 'tu_vung' AND dang = 'chon_mot'
                      AND cau_cha_id IS NULL AND trang_thai = 'da_dang'
                    ORDER BY id LIMIT 20
                """),
                {"c": cap_id},
            ).scalars().all()
            if tv_ids:
                for qid in tv_ids:
                    db.execute(text("UPDATE cau_hoi SET dung_dau_vao = 1 WHERE id = :id"), {"id": int(qid)})

            # Đọc (chon_mot / dung_sai không phụ thuộc hình thiếu)
            doc_rows = db.execute(
                text("""
                    SELECT id, tep_hinh FROM cau_hoi
                    WHERE cap_do_id = :c AND ky_nang = 'doc' AND dang IN ('chon_mot', 'dung_sai')
                      AND cau_cha_id IS NULL AND trang_thai = 'da_dang'
                    ORDER BY (dang = 'chon_mot') DESC, id LIMIT 25
                """),
                {"c": cap_id},
            ).mappings().all()
            picked_doc = 0
            for r in doc_rows:
                if r["tep_hinh"] and not (UPLOADS_DIR / r["tep_hinh"]).is_file():
                    continue
                db.execute(text("UPDATE cau_hoi SET dung_dau_vao = 1 WHERE id = :id"), {"id": int(r["id"])})
                picked_doc += 1
                if picked_doc >= 15:
                    break

            # Nghe (bắt buộc có tệp âm thanh thật trên ổ đĩa!)
            nghe_rows = db.execute(
                text("""
                    SELECT id, tep_audio FROM cau_hoi
                    WHERE cap_do_id = :c AND ky_nang = 'nghe' AND dang IN ('chon_mot', 'dung_sai')
                      AND cau_cha_id IS NULL AND trang_thai = 'da_dang' AND tep_audio IS NOT NULL
                    ORDER BY id
                """),
                {"c": cap_id},
            ).mappings().all()
            picked_nghe = 0
            for r in nghe_rows:
                if (UPLOADS_DIR / r["tep_audio"]).is_file():
                    db.execute(
                        text("UPDATE cau_hoi SET dung_dau_vao = 1, da_kiem_tra_audio = 1 WHERE id = :id"),
                        {"id": int(r["id"])},
                    )
                    picked_nghe += 1
                    if picked_nghe >= 15:
                        break

            # Viết sắp xếp câu có sẵn (HSK 3, HSK 4)
            sx_ids = db.execute(
                text("""
                    SELECT id FROM cau_hoi
                    WHERE cap_do_id = :c AND ky_nang = 'viet' AND dang = 'sap_xep'
                      AND cau_cha_id IS NULL AND trang_thai = 'da_dang'
                    ORDER BY id LIMIT 15
                """),
                {"c": cap_id},
            ).scalars().all()
            for qid in sx_ids:
                db.execute(text("UPDATE cau_hoi SET dung_dau_vao = 1 WHERE id = :id"), {"id": int(qid)})

        # 5. Nạp 16 câu Dịch câu (Câu 7: HSK 1–4) nếu chưa tồn tại
        inserted_dich = 0
        for cap_ma, nhom_ma, noi_dung, pinyin, dich_nghia, tieu_chi, giai_thich, chap_nhan in DICH_CAU_SEED:
            exists = db.execute(
                text("SELECT id FROM cau_hoi WHERE dang = 'dich_cau' AND noi_dung = :nd LIMIT 1"),
                {"nd": noi_dung},
            ).scalar_one_or_none()
            if exists:
                continue
            new_id = next_root_id(db, "cau_hoi")
            db.execute(
                text("""
                    INSERT INTO cau_hoi (
                        id, ma_goc_id, phien_ban, dang, cap_do_id, ky_nang, nhom_kien_thuc_id,
                        dung_on_luyen, dung_thi_thu, dung_dau_vao,
                        noi_dung, pinyin, dich_nghia, tieu_chi_mo_ta, giai_thich,
                        diem_toi_da, nguong_dat, nguon_noi_dung, trang_thai
                    ) VALUES (
                        :id, :id, 1, 'dich_cau', :cap, 'viet', :nhom,
                        0, 0, 1,
                        :nd, :py, :dn, :tc, :gt,
                        10.00, 6.00, 'tu_soan', 'da_dang'
                    )
                """),
                {
                    "id": new_id,
                    "cap": cap_ids[cap_ma],
                    "nhom": topic_ids[nhom_ma],
                    "nd": noi_dung,
                    "py": pinyin,
                    "dn": dich_nghia,
                    "tc": tieu_chi,
                    "gt": giai_thich,
                },
            )
            for idx, ans in enumerate(chap_nhan, start=1):
                db.execute(
                    text("""
                        INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung)
                        VALUES (:q, 'dap_an_chap_nhan', :t, 0, :nd)
                    """),
                    {"q": new_id, "t": idx, "nd": ans},
                )
            inserted_dich += 1

        # 6. Nạp 8 câu Sắp xếp từ cho HSK 1 & HSK 2 (Câu 8 nhánh HSK 1–2) nếu chưa tồn tại
        inserted_sx = 0
        for cap_ma, nhom_ma, nghia_vi, pieces, accepted in SAP_XEP_HSK12_SEED:
            stem = " / ".join(pieces)
            exists = db.execute(
                text("SELECT id FROM cau_hoi WHERE dang = 'sap_xep' AND ky_nang = 'viet' AND dich_nghia = :dn LIMIT 1"),
                {"dn": nghia_vi},
            ).scalar_one_or_none()
            if exists:
                continue
            new_id = next_root_id(db, "cau_hoi")
            db.execute(
                text("""
                    INSERT INTO cau_hoi (
                        id, ma_goc_id, phien_ban, dang, cap_do_id, ky_nang, nhom_kien_thuc_id,
                        dung_on_luyen, dung_thi_thu, dung_dau_vao,
                        noi_dung, dich_nghia, giai_thich, nguon_noi_dung, trang_thai
                    ) VALUES (
                        :id, :id, 1, 'sap_xep', :cap, 'viet', :nhom,
                        1, 0, 1,
                        :nd, :dn, :gt, 'tu_soan', 'da_dang'
                    )
                """),
                {
                    "id": new_id,
                    "cap": cap_ids[cap_ma],
                    "nhom": topic_ids[nhom_ma],
                    "nd": stem,
                    "dn": nghia_vi,
                    "gt": f"Trật tự chuẩn: {accepted[0]} ({nghia_vi})",
                },
            )
            for idx, piece in enumerate(pieces, start=1):
                db.execute(
                    text("""
                        INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung)
                        VALUES (:q, 'lua_chon', :t, 0, :nd)
                    """),
                    {"q": new_id, "t": idx, "nd": piece},
                )
            for idx, acc in enumerate(accepted, start=1):
                db.execute(
                    text("""
                        INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung)
                        VALUES (:q, 'dap_an_chap_nhan', :t, 0, :nd)
                    """),
                    {"q": new_id, "t": idx, "nd": acc},
                )
            inserted_sx += 1

        db.commit()

        # In bảng đối chiếu số câu đánh giá đầu vào theo từng cấp × kỹ năng × dạng câu
        print(f"SEED_DONE: +{inserted_dich} dich_cau, +{inserted_sx} sap_xep HSK1-2")
        summary = db.execute(
            text("""
                SELECT c.ma, q.ky_nang, q.dang, COUNT(*) AS so_cau_dau_vao
                FROM cau_hoi q JOIN cap_do c ON c.id = q.cap_do_id
                WHERE q.dung_dau_vao = 1 AND q.trang_thai = 'da_dang' AND q.cau_cha_id IS NULL
                GROUP BY c.ma, q.ky_nang, q.dang
                ORDER BY c.thu_tu, q.ky_nang, q.dang
            """)
        ).mappings().all()
        for r in summary:
            print(" ", dict(r))
        lech = db.execute(text("SELECT COUNT(*) FROM v_doi_soat_nang_luong WHERE so_du_luu <> so_du_tinh")).scalar_one()
        print("DOI_SOAT_NANG_LUONG_LECH:", lech)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
