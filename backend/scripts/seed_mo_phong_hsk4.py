"""Biên soạn và nạp 7 đề thi mô phỏng chuẩn cấu trúc HSK 2.0 cho cấp HSK 4:
HSK 4 – Đề 4 (H4M04) .. HSK 4 – Đề 10 (H4M10).

Mỗi đề gồm đúng 100 câu tính điểm (45 Nghe phần 1–3 + 40 Đọc phần 4–6 + 15 Viết phần 7–8) + 10 câu ví dụ,
khớp 100% quy chuẩn đề thi thật HSK 4 (kèm băng nghe MP3 phát 1 lần chuẩn HSK 4 và 5 câu viết nhìn tranh đặt câu).
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._hsk4_pool_a import HSK4_POOL_A
from scripts._hsk4_pool_b import HSK4_POOL_B
from scripts._sim_exam_helper import LETTER, opts_text, save_and_seed_exams, tf


def make_hsk4_exam(cfg: dict) -> tuple[str, dict]:
    code = cfg["code"]
    slug = f"hsk4_{code.lower()}"
    plan: list[dict] = []

    # Part 1: Nghe 1–10 (Đúng/Sai ★; 2 ví dụ + 10 câu tính điểm)
    l1_rows = [
        (True, True, "★ 他打算下午去银行。", "我想去办个信用卡，今天下午你有时间吗？陪我去一趟银行？\n★ 他打算下午去银行。"),
        (True, False, "★ 他喜欢看电视广告。", "现在我很少看电视，其中一个原因是，广告太多了，不管什么时间，也不管什么节目，只要你打开电视，总能看到那么多的广告，浪费我的时间。\n★ 他喜欢看电视广告。"),
        *[(False, ok, f"★ {stmt}", f"{mono}\n★ {stmt}") for ok, stmt, mono in cfg["L1"]],
    ]
    for ex, ok, s, said in l1_rows:
        plan.append({
            "part": 1, "ex": ex,
            "q": {"dang": "dung_sai", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "loi_nghe": said, "phuong_an": tf(ok)},
        })

    # Part 2: Nghe 11–25 (1 ví dụ + 15 câu tính điểm)
    l2_rows = [
        (True, "D", ["去机场", "快到了", "油是满的", "有加油站"], "女：该加油了，去机场的路上有加油站吗？\n男：有，你放心吧。\n问：男的主要是什么意思？"),
        *[(False, *r) for r in cfg["L2"]],
    ]
    for ex, ans, ops, said in l2_rows:
        plan.append({
            "part": 2, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(ops, ans)},
        })

    # Part 3: Nghe 26–35 (1 ví dụ + 10 câu hội thoại dài) + 36–45 (5 đoạn văn × 2 câu)
    l3_single_rows = [
        (True, "C", ["两点", "3点", "3：30", "6点"], "男：把这个文件复印五份，一会儿拿到会议室发给大家。\n女：好的。会议是下午三点吗？\n男：改了。三点半，推迟了半个小时。\n女：好，六零二会议室没变吧？\n男：对，没变。\n问：会议几点开始？"),
        *[(False, *r) for r in cfg["L3_SINGLE"]],
    ]
    for ex, ans, ops, said in l3_single_rows:
        plan.append({
            "part": 3, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False,
                  "loi_nghe": said, "phuong_an": opts_text(ops, ans)},
        })
    for passage, qs in cfg["L3_GROUPS"]:
        plan.append({
            "part": 3,
            "group": {"dang": "ngu_lieu", "ky_nang": "nghe", "dung_thi_thu": True, "dung_on_luyen": False, "loi_nghe": passage},
            "children": [[{"dang": "chon_mot", "loi_nghe": q_said, "phuong_an": opts_text(op, ans)}, False] for q_said, ans, op in qs],
        })

    # Part 4: Đọc 46–50 (A–F; D = 坚持 làm ví dụ) & 51–55 (A–F; C = 温度 làm ví dụ)
    plan.append({
        "part": 4,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(cfg["R1A_OPTS"])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "她每天都（　）走路上下班，所以身体一直很不错。", "dap_an_thu_tu": 4}, True],
            *[[{"dang": "chon_bo_chung", "noi_dung": s, "dap_an_thu_tu": LETTER[ans]}, False] for ans, s in cfg["R1A"]],
        ],
    })
    plan.append({
        "part": 4,
        "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "phuong_an": opts_text(cfg["R1B_OPTS"])},
        "children": [
            [{"dang": "chon_bo_chung", "noi_dung": "A：今天真冷啊，好像白天最高（　）才2℃。\nB：刚才电视里说明天更冷。", "dap_an_thu_tu": 3}, True],
            *[[{"dang": "chon_bo_chung", "noi_dung": s, "dap_an_thu_tu": LETTER[ans]}, False] for ans, s in cfg["R1B"]],
        ],
    })

    # Part 5: Đọc 56–65 (Sắp xếp A, B, C)
    r2_rows = [
        (True, "BAC", ("可是今天起晚了", "平时我骑自行车上下班", "所以就打车来公司")),
        *[(False, *r) for r in cfg["R2"]],
    ]
    for ex, order, (a, b, c) in r2_rows:
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

    # Part 6: Đọc 66–79 (1 ví dụ + 14 câu đơn) + 80–85 (3 đoạn × 2 câu)
    r3_single_rows = [
        (True, "A", ["幽默", "马虎", "骄傲", "害羞"], "她很活泼，说话很有趣，总能给我们带来快乐，我们都很喜欢和她在一起。\n★ 她是个什么样的人？"),
        *[(False, *r) for r in cfg["R3_SINGLE"]],
    ]
    for ex, ans, ops, s in r3_single_rows:
        plan.append({
            "part": 6, "ex": ex,
            "q": {"dang": "chon_mot", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": s, "phuong_an": opts_text(ops, ans)},
        })
    for passage, qs in cfg["R3_GROUPS"]:
        plan.append({
            "part": 6,
            "group": {"dang": "ngu_lieu", "ky_nang": "doc", "dung_thi_thu": True, "dung_on_luyen": False, "noi_dung": passage},
            "children": [[{"dang": "chon_mot", "noi_dung": q_s, "phuong_an": opts_text(op, ans)}, False] for q_s, ans, op in qs],
        })

    # Part 7: Viết 86–95 (Sắp xếp từ thành câu)
    w1_rows = [
        (True, ["那座桥", "800年的", "历史", "有", "了"], ["那座桥有800年的历史了。"]),
        *[(False, *r) for r in cfg["W1"]],
    ]
    for ex, pieces, acc in w1_rows:
        plan.append({
            "part": 7, "ex": ex,
            "q": {"dang": "sap_xep", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                  "noi_dung": "完成句子。", "phuong_an": [{"noi_dung": p} for p in pieces], "dap_an_chap_nhan": acc},
        })

    # Part 8: Viết 96–100 (Nhìn tranh dùng từ đặt câu)
    w2_rows = [
        (True, "exams/hsk4_h41002/img/000.jpg", "乒乓球", "她很喜欢打乒乓球。"),
        *[(False, *r) for r in cfg["W2"]],
    ]
    for ex, pic_path, word, sample in w2_rows:
        plan.append({
            "part": 8, "ex": ex,
            "q": {
                "dang": "viet_mo", "ky_nang": "viet", "dung_thi_thu": True, "dung_on_luyen": False,
                "noi_dung": "看图，用词造句。",
                "tep_hinh": pic_path,
                "tu_bat_buoc": word,
                "tieu_chi_mo_ta": "Viết một câu hoàn chỉnh, đúng ngữ pháp, có dùng từ cho sẵn và phù hợp với nội dung hình.",
                "diem_toi_da": 10,
                "nguong_dat": 6,
                "giai_thich": f"Câu tham khảo: {sample}",
            },
        })

    return f"{slug}.json", {
        "exam": {
            "code": code,
            "level": "HSK4",
            "ten": cfg["ten"],
            "phut": 105,
            "nguon": "Đề mô phỏng biên soạn chuẩn cấu trúc HSK 2.0 (HSK 四级)",
            "audio": f"exams/{slug}/listening.mp3",
        },
        "plan": plan,
    }


def main() -> int:
    specs = [make_hsk4_exam(cfg) for cfg in (HSK4_POOL_A + HSK4_POOL_B)]
    save_and_seed_exams(specs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
