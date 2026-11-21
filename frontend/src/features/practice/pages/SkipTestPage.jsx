import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import Icon from "../../../shared/components/Icon.jsx";
import { useTheme } from "../../../shared/theme.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { mediaUrl } from "../../lecturer/utils/labels.js";
import "../../../layouts/staffShell.css";
import HanziText from "../../mock_test/components/HanziText.jsx";
import "../../mock_test/styles/mockTest.css";
import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
import "../../ai_tutor/styles/xiangChat.css";
import { abandonSkip, askSkipXiang, getSkip, saveSkipAnswer, startLevelTest, startSkip, submitSkip } from "../api/practiceApi.js";
import { CHOICE, LATIN, Option, SKILL } from "../guest/LessonParts.jsx";
import { skillSlug } from "../skills.js";
import "../styles/practice.css";
import "../styles/skipTest.css";
import SentenceBuilder, { isPieceList, pickDistractors } from "../../../shared/components/SentenceBuilder.jsx";

function stemOf(q) {
  if (q.dang === "dung_sai") return "Đúng hay sai?";
  if (q.dang === "dien_chu") return "Điền vào chỗ trống";
  if (q.dang === "sap_xep") return "Sắp xếp thành câu đúng";
  return "Chọn đáp án đúng";
}

// Lấy mảng tin nhắn từ lời gọi của XiangChat (dù gọi theo kiểu nào)
function pickMessages(args) {
  for (const a of args) {
    if (Array.isArray(a)) return a;
    if (a && typeof a === "object" && Array.isArray(a.tin_nhan)) return a.tin_nhan;
  }
  return [];
}

function answered(item) {
  return item.tra_loi?.phuong_an_chon_id != null || !!item.tra_loi?.van_ban;
}

// Nhãn theo loại kiểm tra: Vượt đến thửa / Bắt đầu cấp / Vượt chặng (mục 4.2)
function kindText(data) {
  const t = data.thua;
  if (data.loai === "bat_dau_cap") {
    return { tag: `Bắt đầu ${t.ten_cap_do}`, meta: "Kiểm tra bắt đầu cấp", resume: "Kiểm tra bắt đầu cấp",
      pass: "Mở cấp thành công!", gain: `Đã mở ${t.ten_cap_do} cho kỹ năng ${SKILL[t.ky_nang]}.`, need: "để mở cấp" };
  }
  if (data.loai === "vuot_chang") {
    return { tag: `Vượt cấp ${t.ten_cap_do}`, meta: "Kiểm tra vượt cấp", resume: "Làm kiểm tra vượt cấp",
      pass: "Vượt cấp thành công!", need: "để vượt cấp",
      gain: data.cap_ke ? `Đã mở ${data.cap_ke.ten} cho kỹ năng ${SKILL[t.ky_nang]}.` : `Bạn đã hoàn thành lộ trình ${SKILL[t.ky_nang]}.` };
  }
  return { tag: `Vượt tới ${t.ten}`, meta: "Kiểm tra vượt", resume: "Vượt tới thửa này", pass: "Vượt thành công!",
    gain: `Đã mở "${t.ten}". Các thửa trước được đánh dấu Đã vượt.`, need: "để vượt" };
}

// Kiểm tra "Vượt đến thửa", "Bắt đầu cấp", "Vượt chặng" (mục 4.2): giấu đáp án đến khi nộp, không tốn năng lượng
export default function SkipTestPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [index, setIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState(null); // "exit" | "submit"
  const [chatQ, setChatQ] = useState(null); // cau_hoi_id đang hỏi Xiang (chỉ sau khi nộp)

  const load = useCallback((signal) => getSkip(token, luotId, signal).then((d) => {
    setData(d);
    if (d.trang_thai === "dang_lam") setIndex(Math.max(0, d.cau_hoi.findIndex((i) => !answered(i))));
  }), [token, luotId]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError("");
    load(controller.signal).catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài kiểm tra"));
    return () => controller.abort();
  }, [load]);

  const mapUrl = data ? `/hoc-vien/on-luyen/${skillSlug(data.thua.ky_nang)}?cap=${data.thua.cap_do_id}` : "/hoc-vien/on-luyen";
  useEffect(() => {
    if (data?.trang_thai === "da_bo") navigate(mapUrl, { replace: true });
  }, [data, mapUrl, navigate]);

  const items = data?.cau_hoi ?? [];
  const current = items[index];
  const doneCount = items.filter(answered).length;

  async function choose(body) {
    if (!current || data.trang_thai !== "dang_lam") return;
    const before = current.tra_loi;
    setData((d) => ({ ...d, cau_hoi: d.cau_hoi.map((i, n) => (n === index ? { ...i, tra_loi: body } : i)) }));
    try {
      await saveSkipAnswer(token, luotId, current.cau_hoi.id, body);
      setError("");
    } catch (err) {
      setData((d) => ({ ...d, cau_hoi: d.cau_hoi.map((i, n) => (n === index ? { ...i, tra_loi: before } : i)) }));
      setError(err?.message || "Chưa lưu được câu trả lời, hãy thử lại");
    }
  }

  async function submit() {
    setBusy(true); setError("");
    try {
      const d = await submitSkip(token, luotId);
      setData(d); setDialog(null); setIndex(0);
    } catch (err) {
      setError(err?.message || "Chưa nộp được, hãy thử lại");
      setDialog(null);
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    setBusy(true); setError("");
    try {
      const res = data.loai && data.loai !== "vuot_thua"
        ? await startLevelTest(token, data.thua.cap_do_id, data.thua.ky_nang, data.loai === "vuot_chang" ? "vuot-chang" : "bat-dau-cap")
        : await startSkip(token, data.thua.ma_goc_id);
      navigate(`/on-luyen/vuot/${res.luot_id}`, { replace: true });
    } catch (err) {
      setError(err?.message || "Không mở lại được kiểm tra");
    } finally {
      setBusy(false);
    }
  }

  async function abandon() {
    setBusy(true);
    try { await abandonSkip(token, luotId); } finally { setBusy(false); navigate(mapUrl); }
  }

  const shell = (body, footer) => (
    <div className="xg xc sl sk" data-theme={theme}>
      <div className="sl-wrap">
        <header className="sl-top">
          <button type="button" className="sl-x" aria-label="Thoát" onClick={() => (data?.trang_thai === "dang_lam" ? setDialog("exit") : navigate(mapUrl))}>
            <Icon name="x" />
          </button>
          <span className="sl-progress" role="progressbar" aria-valuemin={0} aria-valuemax={items.length || 1} aria-valuenow={doneCount}
            aria-label="Số câu đã trả lời"><i style={{ width: `${items.length ? (100 * doneCount) / items.length : 0}%` }} /></span>
          {data && <span className="sl-tag"><Icon name="bolt" size={14} /> {kindText(data).tag}</span>}
        </header>
        <main className="sl-main">{body}</main>
      </div>
      {footer}
      {dialog && (
        <div className="xt-dialog sl-dialog" role="dialog" aria-modal="true" aria-labelledby="sk-dlg">
          <div className="xt-dialog__box">
            {dialog === "exit" ? (
              <>
                <h2 id="sk-dlg">Rời bài kiểm tra?</h2>
                <p>Câu đã chọn được giữ lại, lần sau bấm "{data && kindText(data).resume}" sẽ làm tiếp. Chưa nộp thì chưa có kết quả.</p>
                <div className="sl-dialog__acts">
                  <button type="button" className="xc-btn xc-btn--sm" onClick={() => setDialog(null)}>Làm tiếp</button>
                  <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => navigate(mapUrl)}>Thoát, giữ bài</button>
                  <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" disabled={busy} onClick={abandon}>Bỏ lượt</button>
                </div>
              </>
            ) : (
              <>
                <h2 id="sk-dlg">Nộp bài?</h2>
                <p>{doneCount < items.length ? `Còn ${items.length - doneCount} câu chưa trả lời, câu trống tính là sai. ` : ""}Cần đúng {items.length}/{items.length} {data && kindText(data).need}.</p>
                <div className="sl-dialog__acts">
                  <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setDialog(null)}>Xem lại</button>
                  <button type="button" className="xc-btn xc-btn--sm" disabled={busy} onClick={submit}>{busy ? "Đang nộp..." : "Nộp bài"}</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );

  if (error && !data) return shell(<p role="alert">{error}</p>);
  if (!data) return shell(<p className="xc-muted">Đang tải bài kiểm tra...</p>);

  if (data.trang_thai === "da_nop" && data.ket_qua) {
    const r = data.ket_qua;
    return shell(
      <div className={`sl-done${r.dat ? " is-pass" : ""}`}>
        <span className="sl-seal hz" aria-hidden="true">{r.dat ? "过" : "再"}</span>
        <p className="sl-meta">{kindText(data).meta} · {SKILL[data.thua.ky_nang]} · {data.thua.ten_cap_do}</p>
        <h1>{r.dat ? kindText(data).pass : "Chưa đạt"}</h1>
        <p className="sl-score"><b>{r.so_dung}/{r.tong}</b> câu đúng · cần đúng {r.tong}/{r.tong}</p>
        <p className="sl-gain">
          {r.dat ? `${kindText(data).gain}${r.kn ? ` +${r.kn} KN` : ""}`
            : "Tiến độ giữ nguyên. Bạn có thể làm lại kiểm tra bất cứ lúc nào."}
        </p>
        <ol className="sk-review">
          {items.map((it) => {
            const k = it.ket_qua;
            const chosen = it.phuong_an.find((o) => o.id === it.tra_loi?.phuong_an_chon_id);
            const right = it.phuong_an.find((o) => o.id === k.dap_an_id);
            return (
              <li key={it.thu_tu} className={k.dung ? "is-ok" : "is-bad"}>
                <span className="sk-review__mark" aria-label={k.dung ? "Đúng" : "Sai"}>{k.dung ? <Icon name="check" size={16} /> : "!"}</span>
                <div>
                  <p className="sk-review__q">
                    <b>Câu {it.thu_tu}.</b>{" "}
                    {it.cau_hoi.noi_dung && (LATIN.test(it.cau_hoi.noi_dung) ? it.cau_hoi.noi_dung : <span className="hz">{it.cau_hoi.noi_dung}</span>)}
                  </p>
                  <p>Bạn chọn: <strong>{chosen ? <Option option={chosen} /> : it.tra_loi?.van_ban || "Bỏ trống"}</strong></p>
                  {!k.dung && (right || k.dap_an_chap_nhan.length > 0) && (
                    <p>Đáp án: <strong>{right ? <Option option={right} /> : <span className="hz">{k.dap_an_chap_nhan.join(" / ")}</span>}</strong></p>
                  )}
                  {k.giai_thich && <p className="sk-review__note">{k.giai_thich}</p>}
                  {k.dich_nghia && <p className="sk-review__note">{k.dich_nghia}</p>}
                  {chatQ !== it.cau_hoi.id ? (
                    <button type="button" className="xx-open sk-ask" onClick={() => setChatQ(it.cau_hoi.id)}>
                      <img src={xiangFace} alt="" />Hỏi Xiang
                    </button>
                  ) : (
                    <div className="sl-q sk-chat">
                      <XiangChat key={it.cau_hoi.id} luotId={null} cauHoiId={it.cau_hoi.id} defaultOpen onClose={() => setChatQ(null)}
                        ask={(...args) => askSkipXiang(token, luotId, { cau_hoi_id: it.cau_hoi.id, tin_nhan: pickMessages(args) })} />
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
        {r.so_dung < r.tong && <p className="sl-note">Câu sai và câu bỏ trống đã được lưu vào Sổ tay.</p>}
        <div className="sl-done__acts">
          {r.dat ? (
            <button type="button" className="xc-btn" onClick={() => navigate(mapUrl)}>Về bản đồ <Icon name="arrow" /></button>
          ) : (
            <>
              <button type="button" className="xc-btn xc-btn--plain" onClick={() => navigate(mapUrl)}>Để sau</button>
              <button type="button" className="xc-btn" disabled={busy} onClick={retry}>Làm lại kiểm tra</button>
            </>
          )}
        </div>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  }

  if (!current) return shell(<p className="xc-muted">Không có câu hỏi.</p>);
  const q = current.cau_hoi;
  const last = index === items.length - 1;

  const footer = (
    <footer className="sl-foot">
      <div className="sl-foot__in sk-foot">
        {error && <p role="alert">{error}</p>}
        <button type="button" className="xc-btn xc-btn--plain" disabled={index === 0} onClick={() => setIndex(index - 1)}>Câu trước</button>
        {last
          ? <button type="button" className="xc-btn" onClick={() => setDialog("submit")}>Nộp bài</button>
          : <button type="button" className="xc-btn" onClick={() => setIndex(index + 1)}>Câu sau</button>}
      </div>
    </footer>
  );

  return shell(
    <div className="sl-q">
      <nav className="sk-dots" aria-label="Danh sách câu">
        {items.map((it, n) => (
          <button key={it.thu_tu} type="button" className={`sk-dot${n === index ? " is-on" : ""}${answered(it) ? " is-done" : ""}`}
            aria-current={n === index ? "step" : undefined} aria-label={`Câu ${it.thu_tu}${answered(it) ? ", đã trả lời" : ""}`}
            onClick={() => setIndex(n)}>{it.thu_tu}</button>
        ))}
      </nav>
      <p className="sl-meta">Câu {current.thu_tu}/{items.length} · Không tốn năng lượng · Đáp án hiện sau khi nộp</p>
      <h1>{stemOf(q)}</h1>
      {current.ngu_lieu && (current.ngu_lieu.noi_dung || current.ngu_lieu.tep_hinh) && (
        <div className="sl-passage">
          {current.ngu_lieu.tep_hinh && <img src={mediaUrl(current.ngu_lieu.tep_hinh)} alt="" />}
          {current.ngu_lieu.noi_dung && <HanziText text={current.ngu_lieu.noi_dung} pinyin={current.ngu_lieu.pinyin} />}
        </div>
      )}
      {(q.tep_audio || current.ngu_lieu?.tep_audio) && <audio className="sl-audio" controls src={mediaUrl(q.tep_audio || current.ngu_lieu.tep_audio)} />}
      {((q.noi_dung && !isPieceList(q.noi_dung)) || q.tep_hinh) && (
        <div className={`sl-stem${q.noi_dung && !LATIN.test(q.noi_dung) && q.noi_dung.length <= 4 ? " sl-stem--word" : ""}`}>
          {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} />}
          {q.noi_dung && !isPieceList(q.noi_dung) && (LATIN.test(q.noi_dung) ? <p>{q.noi_dung}</p> : <HanziText text={q.noi_dung} pinyin={q.pinyin} />)}
        </div>
      )}
      {CHOICE.includes(q.dang) ? (
        <div className={`sl-opts${current.phuong_an.some((o) => o.tep_hinh) ? " sl-opts--img" : ""}`} role="radiogroup" aria-label="Phương án">
          {current.phuong_an.map((o, i) => (
            <button key={o.id} type="button" role="radio" aria-checked={o.id === current.tra_loi?.phuong_an_chon_id}
              className={`sl-opt${o.id === current.tra_loi?.phuong_an_chon_id ? " is-picked" : ""}`}
              onClick={() => choose({ phuong_an_chon_id: o.id, van_ban: null })}>
              <kbd>{i + 1}</kbd><Option option={o} />
            </button>
          ))}
        </div>
      ) : (
        q.dang === "sap_xep" && current.phuong_an?.length ? (
          <SentenceBuilder key={q.id} pieces={current.phuong_an} extra={pickDistractors(items, current)} prompt={q.nghia_cau} value={current.tra_loi?.van_ban || ""}
            onChange={(v) => choose({ phuong_an_chon_id: null, van_ban: v || null })} />
        ) : (
          <input key={q.id} className="sl-input hz" defaultValue={current.tra_loi?.van_ban || ""} maxLength={200} aria-label="Câu trả lời"
            onBlur={(e) => e.target.value.trim() !== (current.tra_loi?.van_ban || "") && choose({ phuong_an_chon_id: null, van_ban: e.target.value.trim() || null })} />
        )
      )}
    </div>,
    footer
  );
}
