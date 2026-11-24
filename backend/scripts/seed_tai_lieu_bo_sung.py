"""Tạo và đăng bổ sung 6 tài liệu PDF chuẩn Unicode (Việt – Trung – Pinyin) cho kho Học liệu HSK 1–4:

1. Sổ tay Từ vựng & Ví dụ trọng tâm HSK 1 (cap=HSK1, ky_nang=tu_vung)
2. Sổ tay Từ vựng & Ví dụ trọng tâm HSK 2 (cap=HSK2, ky_nang=tu_vung)
3. Sổ tay Từ vựng & Ví dụ trọng tâm HSK 3 (cap=HSK3, ky_nang=tu_vung)
4. Sổ tay Từ vựng & Ví dụ trọng tâm HSK 4 (cap=HSK4, ky_nang=tu_vung)
5. Cẩm nang Ngữ pháp & Ghép câu Viết HSK 1 (cap=HSK1, ky_nang=viet)
6. Cẩm nang Ngữ pháp & Ghép câu Viết HSK 2 (cap=HSK2, ky_nang=viet)

Đồng thời gắn tai_lieu_id tương ứng (theo cấp + kỹ năng) vào các bài ôn luyện chưa gắn tài liệu tham khảo.
An toàn khi chạy lại nhiều lần (idempotent).
"""
from pathlib import Path
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fpdf import FPDF
from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.materials.endpoints.lecturer_materials import MaterialIn
from app.modules.materials.services import material_service
from app.storage.private_files import delete_file, save_document

DATA_DIR = Path(__file__).resolve().parent / "data" / "cam_nang"
SOURCE = "Nhóm Xianglingo biên soạn; bám sát khung từ vựng và ngữ pháp HSK 2.0 (国家汉办)"

WIN_FONTS = Path(r"C:\Windows\Fonts")
FONT_VI = WIN_FONTS / "segoeui.ttf"
FONT_VI_BOLD = WIN_FONTS / "segoeuib.ttf"
FONT_ZH = WIN_FONTS / "msyh.ttc"
FONT_ZH_BOLD = WIN_FONTS / "msyhbd.ttc"


class StudyPdf(FPDF):
    def __init__(self, doc_title: str, subtitle: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = doc_title
        self.subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=16)
        self.add_font("ViFont", "", str(FONT_VI))
        self.add_font("ViFont", "B", str(FONT_VI_BOLD))
        self.add_font("ZhFont", "", str(FONT_ZH))
        if FONT_ZH_BOLD.is_file():
            self.add_font("ZhFont", "B", str(FONT_ZH_BOLD))
        else:
            self.add_font("ZhFont", "B", str(FONT_ZH))
        self.set_fallback_fonts(["ZhFont"])

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("ViFont", "", 8.5)
        self.set_text_color(110, 118, 129)
        self.cell(0, 6, f"Xianglingo · {self.doc_title}", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("ViFont", "", 8.5)
        self.set_text_color(130, 136, 145)
        self.cell(0, 6, f"Trang {self.page_no()} · Học liệu nội bộ Xianglingo", align="C")

    def add_cover_banner(self, badge: str):
        self.add_page()
        self.set_fill_color(185, 43, 39)
        self.rect(14, 14, 182, 30, style="F")
        self.set_xy(20, 18)
        self.set_font("ViFont", "B", 9.5)
        self.set_text_color(255, 228, 220)
        self.cell(0, 6, badge.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_x(20)
        self.set_font("ViFont", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, self.doc_title, new_x="LMARGIN", new_y="NEXT")
        self.set_x(20)
        self.set_font("ViFont", "", 9.5)
        self.set_text_color(255, 240, 236)
        self.cell(0, 6, self.subtitle, new_x="LMARGIN", new_y="NEXT")
        self.set_y(50)
        self.set_text_color(30, 35, 42)

    def section_heading(self, title: str):
        if self.get_y() > 250:
            self.add_page()
        self.ln(3)
        self.set_fill_color(252, 242, 240)
        self.set_draw_color(185, 43, 39)
        y = self.get_y()
        self.line(14, y, 14, y + 8)
        self.set_x(16)
        self.set_font("ViFont", "B", 12)
        self.set_text_color(155, 28, 28)
        self.cell(180, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(30, 35, 42)

    def paragraph(self, text_body: str):
        self.set_font("ViFont", "", 10)
        self.set_text_color(45, 52, 60)
        self.multi_cell(0, 5.8, text_body)
        self.ln(1.5)

    def bullet_list(self, items: list[str]):
        for item in items:
            if self.get_y() > 268:
                self.add_page()
            self.set_font("ViFont", "", 10)
            self.set_text_color(45, 52, 60)
            self.set_x(16)
            self.multi_cell(178, 5.8, f"•  {item}")
        self.ln(1.5)


VOCAB_TIPS = {
    1: [
        "HSK 1 tập trung vào 150 từ giao tiếp sinh tồn: đại từ nhân xưng, số đếm, thời gian, gia đình, ăn uống và đi lại.",
        "Học từ luôn gắn kèm lượng từ chuẩn: 一个人 (một người), 一本书 (một quyển sách), 一杯茶 (một tách trà), 一件衣服 (một chiếc áo).",
        "Đọc to câu ví dụ theo Pinyin 3 lần trước khi che Pinyin để mắt quen mặt chữ Hán tự nhiên.",
    ],
    2: [
        "HSK 2 mở rộng lên nhóm động từ sinh hoạt, tính từ cảm xúc, phương tiện giao thông và các cặp liên từ cơ bản.",
        "Đặc biệt chú ý các động từ ly hợp (跑步, 游泳, 跳舞, 唱歌, 生病, 起床): trợ từ và thời lượng đặt ở giữa hai chữ.",
        "Ôn kết hợp Thẻ lật từ vựng trên Xianglingo trước mỗi bài để ghi nhớ sâu ngữ cảnh câu.",
    ],
    3: [
        "Từ HSK 3 trở đi, đề thi chính thức KHÔNG còn in Pinyin trên đề giấy; cần nhận diện thẳng mặt chữ Hán.",
        "Chú ý nhóm từ hai âm tiết dễ nhầm thanh điệu và các động từ đi kèm bổ ngữ kết quả / xu hướng (打扫干净, 搬进来, 解决好).",
        "Mỗi ngày chọn 10 từ đặt câu ngắn hoặc luyện ghép câu ở mục Ôn luyện Viết để chuyển từ vựng thụ động thành chủ động.",
    ],
    4: [
        "HSK 4 đòi hỏi phân biệt sắc thái từ gần nghĩa trong công sở, học thuật và nghị luận xã hội.",
        "Nắm chắc các cặp từ hay thi ở Phần 1 Đọc hiểu: 经验 (kinh nghiệm) / 经历 (trải nghiệm); 尽管 (mặc dù + sự thật) / 不管 (bất kể + nghi vấn); 居然 (bất ngờ) / 果然 (đúng như đoán); 适合 (động từ: hợp với) / 合适 (tính từ: vừa vặn, phù hợp).",
        "Khi đọc câu ví dụ, hãy gạch chân giới từ và danh từ đi kèm cố định (ví dụ: 由…负责, 给…留下印象, 获得成功).",
    ],
}


def build_vocab_pdf(cap: int, words: list[dict], out_path: Path) -> bytes:
    title = f"Sổ tay Từ vựng & Ví dụ trọng tâm HSK {cap}"
    sub = f"Tổng hợp {len(words)} từ vựng cốt lõi kèm Pinyin, nghĩa tiếng Việt và câu ví dụ thực tế"
    pdf = StudyPdf(title, sub)
    pdf.add_cover_banner(f"Học liệu Từ vựng · Cấp HSK {cap}")

    pdf.section_heading(f"1. Phương pháp học từ vựng HSK {cap} hiệu quả")
    pdf.bullet_list(VOCAB_TIPS[cap])

    pdf.section_heading(f"2. Bảng tra cứu {len(words)} từ vựng & câu ví dụ chuẩn HSK {cap}")
    pdf.paragraph("Mỗi mục gồm: Chữ Hán — Phiên âm Pinyin — Nghĩa tiếng Việt cốt lõi và câu ví dụ đặt trong ngữ cảnh giao tiếp chuẩn.")

    for idx, w in enumerate(words, start=1):
        if pdf.get_y() > 256:
            pdf.add_page()
        y0 = pdf.get_y()
        if idx % 2 == 0:
            pdf.set_fill_color(248, 249, 251)
            pdf.rect(14, y0, 182, 14.5 if w.get("vd_cau") else 8.5, style="F")

        pdf.set_xy(16, y0 + 1)
        pdf.set_font("ViFont", "B", 10.5)
        pdf.set_text_color(165, 28, 28)
        head = f"{idx}. {w['chu_han']}   [{w['pinyin']}]"
        pdf.cell(68, 6, head)

        pdf.set_font("ViFont", "B", 10)
        pdf.set_text_color(28, 35, 43)
        pdf.multi_cell(110, 6, w["nghia"])

        if w.get("vd_cau"):
            pdf.set_x(22)
            pdf.set_font("ViFont", "", 9.2)
            pdf.set_text_color(75, 85, 99)
            ex_line = f"VD: {w['vd_cau']}"
            if w.get("vd_pinyin"):
                ex_line += f" ({w['vd_pinyin']})"
            if w.get("vd_nghia"):
                ex_line += f" — {w['vd_nghia']}"
            pdf.multi_cell(172, 5.2, ex_line)
        pdf.ln(1.2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = bytes(pdf.output())
    out_path.write_bytes(data)
    return data


WRITING_GUIDES = {
    1: {
        "ten": "Cẩm nang Ngữ pháp & Ghép câu Viết HSK 1",
        "mo_ta": "Quy tắc trật tự câu tiếng Trung cơ bản, vị trí thời gian – nơi chốn, câu phủ định, câu hỏi và bài tập mẫu HSK 1.",
        "tep": "cam_nang_hsk1_viet.pdf",
        "sections": [
            ("1. Công thức vàng về trật tự câu HSK 1", [
                "Khác với tiếng Việt, trạng ngữ chỉ THỜI GIAN và ĐỊA ĐIỂM trong tiếng Trung luôn đứng TRƯỚC động từ chính:",
                "Công thức chuẩn: Chủ ngữ + [Thời gian] + [Ở đâu: 在 + Địa điểm] + Động từ + Tân ngữ.",
                "Ví dụ 1: 我 明天 去 学校。 (Wǒ míngtiān qù xuéxiào — Ngày mai tôi đi học.)",
                "Ví dụ 2: 我妈妈 在 医院 工作。 (Wǒ māma zài yīyuàn gōngzuò — Mẹ tôi làm việc ở bệnh viện; tuyệt đối không viết '工作在医院').",
                "Thứ tự thời gian luôn đi từ LỚN đến NHỎ: Năm (年) → Tháng (月) → Ngày (号) → Thứ (星期) → Buổi (上午/下午) → Giờ (点).",
                "Ví dụ 3: 今天 八月 十号 星期五。 (Hôm nay là thứ Sáu ngày 10 tháng 8.)",
            ]),
            ("2. Định ngữ sở hữu & Cụm danh từ với 的", [
                "Mọi thành phần bổ nghĩa cho danh từ (của ai, nước nào, như thế nào) đều đứng TRƯỚC danh từ trung tâm:",
                "Công thức: [Người sở hữu + 的] + [Số từ + Lượng từ] + [Đặc điểm] + Danh từ chính.",
                "Ví dụ: 他 是 我 的 中国 朋友。 (Anh ấy là người bạn Trung Quốc của tôi.)",
                "Lưu ý: Khi nói quan hệ gia đình gần gũi hoặc đơn vị gắn bó có thể lược bớt 的: 我爸爸 (bố tôi), 我家 (nhà tôi), 我们学校 (trường chúng tôi).",
            ]),
            ("3. Phân biệt hai phó từ phủ định 不 và 没", [
                "Dùng 不 (bù) cho hiện tại, tương lai, thói quen, mong muốn hoặc đi với động từ 是 / tính từ: 我不是老师 (Tôi không phải giáo viên), 今天不冷 (Hôm nay không lạnh).",
                "Dùng 没 (méi) khi phủ định động từ 有 (没有 = không có) HOẶC hành động chưa xảy ra trong quá khứ: 昨天他没去学校 (Hôm qua anh ấy đã không đến trường).",
                "Bẫy hay gặp: Đã có 没 ở trước động từ thì cuối câu KHÔNG thêm 了.",
            ]),
            ("4. Năm mẫu câu hỏi cốt lõi HSK 1", [
                "Câu hỏi Có/Không với 吗: Đặt 吗 cuối câu trần thuật — 你会说汉语吗？ (Bạn biết nói tiếng Hán không?)",
                "Câu hỏi đại từ nghi vấn (谁 ai, 什么 cái gì, 哪儿 ở đâu, 怎么 thế nào): Từ để hỏi giữ nguyên vị trí của thành phần cần hỏi — 这个汉字怎么写？ (Chữ Hán này viết thế nào?)",
                "Hỏi số lượng: 几 + Lượng từ (thường hỏi số nhỏ < 10: 你家有几口人？); 多少 + (Lượng từ) (hỏi số lớn hoặc giá tiền: 这个杯子多少钱？).",
                "Câu tồn hiện chỉ vị trí: Địa điểm + phương vị từ + 有 + Số lượng + Danh từ — 桌子上有两本书 (Trên bàn có hai cuốn sách).",
            ]),
            ("5. Lộ trình luyện kỹ năng Ghép câu & Điền chữ 7 ngày", [
                "Ngày 1–2: Luyện Thửa 1 (Chào hỏi, giới thiệu tên, gia đình & nghề nghiệp) — chú ý vị trí 在 + địa điểm.",
                "Ngày 3–4: Luyện Thửa 2 (Giờ giấc, ngày tháng, phương vị từ 上/下/里/前/后 và mua sắm).",
                "Ngày 5: Ôn lại các câu Điền chữ Hán hay nhầm nét: 没关系, 不客气, 下午, 请坐, 写汉字.",
                "Ngày 6–7: Hoàn thành Kiểm tra cuối thửa đạt 10/10 để nắm chắc nền tảng lên HSK 2.",
            ]),
        ],
    },
    2: {
        "ten": "Cẩm nang Ngữ pháp & Ghép câu Viết HSK 2",
        "mo_ta": "Cấu trúc câu so sánh 比, khoảng cách 离, trợ từ 了/过/着, bổ ngữ kết quả – thời lượng và liên từ câu ghép HSK 2.",
        "tep": "cam_nang_hsk2_viet.pdf",
        "sections": [
            ("1. Câu khoảng cách 离 và Câu so sánh hơn 比", [
                "Khoảng cách giữa hai địa điểm: Địa điểm A + 离 + Địa điểm B + 很远 / 很近 / 不太远.",
                "Ví dụ: 我家离公司不太远，坐公共汽车二十分钟就到了。 (Tuyệt đối không dùng '从我家离公司').",
                "Câu so sánh hơn: A + 比 + B + Tính từ (+ 一点儿 / 多了 / số lượng cụ thể).",
                "Ví dụ: 今天比昨天冷多了。 / 这件红衣服比那件便宜五十块。",
                "Bẫy cực kỳ quan trọng: Trong câu chữ 比, trước tính từ KHÔNG ĐƯỢC dùng 很, 非常, 真 (Sai: A 比 B 很高 → Đúng: A 比 B 高 / 高一点儿).",
            ]),
            ("2. Ba trợ từ động thái 了 – 过 – 着", [
                "Động từ + 了: Hành động đã hoàn thành — 我已经买好火车票了。 (Tôi đã mua xong vé tàu rồi.)",
                "Động từ + 过: Trải nghiệm đã từng xảy ra trong quá khứ — 你去过北京吗？ / 这部电影我看过一次。 (Phủ định: 没 + Động từ + 过).",
                "Động từ + 着: Trạng thái đang duy trì tiếp diễn — 门开着呢 (Cửa đang mở); 她穿着一件白衬衫 (Cô ấy đang mặc chiếc áo sơ mi trắng).",
            ]),
            ("3. Bổ ngữ kết quả, bổ ngữ trạng thái & thời lượng", [
                "Bổ ngữ kết quả (完 xong, 懂 hiểu, 到 thấy/được, 见 thấy, 干净 sạch, 清楚 rõ): 今天的作业我已经写完了。 / 老师说的话你听懂了吗？",
                "Bổ ngữ trạng thái với 得: Chủ ngữ + Động từ + 得 + (很) + Tính từ — 弟弟每天早上都起得很早。 (Nếu động từ có tân ngữ thì lặp lại động từ: 他说汉语说得很好).",
                "Bổ ngữ thời lượng với động từ ly hợp: Khoảng thời gian đặt GIỮA động từ ly hợp — 他每天早上跑半个小时步 / 我昨天睡了八个小时觉。",
            ]),
            ("4. Các cặp liên từ câu ghép trọng tâm HSK 2", [
                "Quan hệ nhân quả: 因为…，所以… (Vì… cho nên…) — 因为外面下大雨，所以我们不去踢足球了。",
                "Quan hệ nhượng bộ chuyển ý: 虽然…，但是… (Tuy… nhưng…) — 虽然这道题有点儿难，但是很有意思。",
                "Phân biệt 就 (sớm, nhanh, ngay) và 才 (muộn, mãi mới): 八点上课，他七点半就到了 vs 他八点半才到。",
                "Phân biệt 再 (lặp lại ở tương lai: 明天再来) và 又 (lặp lại đã xảy ra: 昨天来了，今天又来了).",
            ]),
            ("5. Mẹo kiểm tra nhanh trước khi bấm Nộp câu ghép từ", [
                "Bước 1: Tìm cặp từ hô ứng trước (因为…所以…, 虽然…但是…, 从…到…, 离…远/近, 比…更…).",
                "Bước 2: Đặt Chủ ngữ + Thời gian lên đầu mệnh đề, tiếp đến là giới từ (在/跟/给/往/比) + danh từ, rồi mới tới Động từ chính + Bổ ngữ.",
                "Bước 3: Đọc nhẩm lại cả câu xem trợ từ (了, 过, 着, 呢, 吧, 吗) đã nằm đúng vị trí chưa.",
            ]),
        ],
    },
}


def build_writing_pdf(cap: int, out_path: Path) -> bytes:
    cfg = WRITING_GUIDES[cap]
    pdf = StudyPdf(cfg["ten"], cfg["mo_ta"])
    pdf.add_cover_banner(f"Cẩm nang Kỹ năng Viết · Cấp HSK {cap}")
    for sec_title, bullets in cfg["sections"]:
        pdf.section_heading(sec_title)
        pdf.bullet_list(bullets)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = bytes(pdf.output())
    out_path.write_bytes(data)
    return data


def publish_doc(db, uid: int, cap_do_id: int, ky_nang: str, ten: str, mo_ta: str, pdf_bytes: bytes) -> int:
    latest = db.execute(
        text("SELECT id, trang_thai FROM tai_lieu WHERE ten = :t ORDER BY ma_goc_id DESC, phien_ban DESC LIMIT 1"),
        {"t": ten},
    ).mappings().first()
    if latest and latest["trang_thai"] == "da_dang":
        print(f"· Đã có tài liệu đang đăng: “{ten}” (#{latest['id']})")
        return int(latest["id"])

    relative = save_document(pdf_bytes, "pdf")
    body = MaterialIn(
        ten=ten,
        mo_ta=mo_ta,
        nguon=SOURCE,
        cap_do_id=cap_do_id,
        ky_nang=ky_nang,
        duong_dan=relative,
    )
    try:
        new_id = (
            material_service.create_material(db, body, uid)
            if latest is None
            else material_service.update_material(db, int(latest["id"]), body, uid)
        )
    except Exception:
        delete_file(relative)
        raise
    material_service.change_status(db, new_id, "dang")
    print(f"→ Đã tạo & đăng tài liệu PDF: “{ten}” (#{new_id}, {len(pdf_bytes) // 1024} KB)")
    return int(new_id)


def main() -> int:
    db = SessionLocal()
    try:
        uid = db.execute(
            text("SELECT u.id FROM nguoi_dung u JOIN vai_tro v ON v.id = u.vai_tro_id WHERE v.ma = 'giang_vien' ORDER BY u.id DESC LIMIT 1")
        ).scalar_one()
        levels = {m: int(i) for m, i in db.execute(text("SELECT ma, id FROM cap_do")).all()}

        # 1. Tạo & đăng 4 Sổ tay Từ vựng HSK 1–4 từ chính kho từ vựng thật trong CSDL
        for cap in (1, 2, 3, 4):
            level_id = levels[f"HSK{cap}"]
            words = [
                dict(r) for r in db.execute(
                    text("""
                        SELECT chu_han, pinyin, nghia, vd_cau, vd_pinyin, vd_nghia
                        FROM tu_vung
                        WHERE cap_do_id = :c AND trang_thai = 'xuat_ban'
                        ORDER BY id
                    """),
                    {"c": level_id},
                ).mappings().all()
            ]
            ten = f"Sổ tay Từ vựng & Ví dụ trọng tâm HSK {cap}"
            mo_ta = (
                f"Bảng tổng hợp {len(words)} từ vựng HSK {cap} cốt lõi kèm Pinyin, nghĩa tiếng Việt, "
                f"câu ví dụ song ngữ và mẹo ghi nhớ nhanh."
            )
            pdf_bytes = build_vocab_pdf(cap, words, DATA_DIR / f"so_tay_tu_vung_hsk{cap}.pdf")
            publish_doc(db, uid, level_id, "tu_vung", ten, mo_ta, pdf_bytes)

        # 2. Tạo & đăng 2 Cẩm nang Ngữ pháp & Ghép câu Viết HSK 1–2
        for cap in (1, 2):
            level_id = levels[f"HSK{cap}"]
            cfg = WRITING_GUIDES[cap]
            pdf_bytes = build_writing_pdf(cap, DATA_DIR / cfg["tep"])
            publish_doc(db, uid, level_id, "viet", cfg["ten"], cfg["mo_ta"], pdf_bytes)

        # 3. Gắn tai_lieu_id tương ứng (cùng cấp + kỹ năng) cho các bài ôn đang trống tai_lieu_id
        linked = db.execute(text("""
            UPDATE bo_de b
            JOIN bo_de thua ON thua.ma_goc_id = b.thua_id AND thua.loai = 'thua'
            JOIN (
                SELECT cap_do_id, ky_nang, MAX(id) AS tl_id
                FROM tai_lieu
                WHERE trang_thai = 'da_dang' AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL
                GROUP BY cap_do_id, ky_nang
            ) tl ON tl.cap_do_id = thua.cap_do_id AND tl.ky_nang = thua.ky_nang
            SET b.tai_lieu_id = tl.tl_id
            WHERE b.loai IN ('bai', 'cuoi_thua') AND b.tai_lieu_id IS NULL
        """)).rowcount
        db.commit()
        print(f"HOÀN TẤT HỌC LIỆU PDF: Đã liên kết tài liệu tham khảo cho {linked} bài ôn luyện.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
