import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import "../../../layouts/staffShell.css";
import HanziText from "../../../shared/components/HanziText.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { CHOICE, FlashCards, LATIN, Option, SKILL, instruction } from "../../../shared/components/LessonParts.jsx";
import SentenceBuilder, { isPieceList, pickDistractors } from "../../../shared/components/SentenceBuilder.jsx";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import { mediaUrl } from "../../../shared/utils/format.js";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import "../../mock_test/styles/mockTest.css";
import { abandonAttempt, checkAnswer, getLessonAttempt, startLesson } from "../api/practiceApi.js";
import "../styles/practice.css";
import { skillSlug } from "../utils/skills.js";

export default function LessonPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [cards, setCards] = useState(false);
  const [pick, setPick] = useState(null);
  const [text, setText] = useState("");
  const [shown, setShown] = useState(null); // thu_tu câu đang hiện phản hồi
  const [busy, setBusy] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const load = useCallback((signal) => getLessonAttempt(token, luotId, signal).then((d) => {
    if (d.trang_thai === "da_bo") { navigate(`/hoc-vien/on-luyen/${skillSlug(d.bai.ky_nang)}?cap=${d.bai.cap_do_id}`, { replace: true }); return; }
    setData(d);
    setCards(d.trang_thai === "dang_lam" && d.the_tu.length > 0 && d.cau_hoi.every((q) => !q.ket_qua));
  }), [token, luotId, navigate]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null); setShown(null); setPick(null); setText("");
    load(controller.signal).catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài"));
    return () => controller.abort();
  }, [load]);

  const mapUrl = data ? `/hoc-vien/on-luyen/${skillSlug(data.bai.ky_nang)}?cap=${data.bai.cap_do_id}` : "/hoc-vien/on-luyen";
  const items = data?.cau_hoi ?? [];
  const current = useMemo(() => {
    if (shown != null) return items.find((i) => i.thu_tu === shown);
    return items.find((i) => !i.ket_qua);
  }, [items, shown]);
  const doneCount = items.filter((i) => i.ket_qua).length;

  async function submit(skip = false) {
    if (!current || busy) return;
    const q = current.cau_hoi;
    const body = { cau_hoi_id: q.id, phuong_an_chon_id: null, van_ban: null };
    if (!skip) {
      if (CHOICE.includes(q.dang)) body.phuong_an_chon_id = pick;
      else body.van_ban = text.trim() || null;
    }
    setBusy(true); setError("");
    try {
      const res = await checkAnswer(token, luotId, body);
      setData((d) => ({
        ...d, nang_luong: res.nang_luong, kn: res.kn, xong: res.ket_thuc,
        cau_hoi: d.cau_hoi.map((i) => (i.thu_tu === current.thu_tu
          ? { ...i, tra_loi: { phuong_an_chon_id: body.phuong_an_chon_id, van_ban: body.van_ban }, ket_qua: res.ket_qua } : i)),
      }));
      setShown(current.thu_tu);
    } catch (err) {
      setError(err?.message || "Chưa kiểm tra được, hãy thử lại");
    } finally {
      setBusy(false);
    }
  }

  async function next() {
    setPick(null); setText(""); setShown(null); setChatOpen(false);
    if (data.xong) {
      setBusy(true);
      try { await load(); } finally { setBusy(false); }
    }
  }

  async function restart() {
    setBusy(true); setError("");
    try {
      if (data.trang_thai === "dang_lam") await abandonAttempt(token, luotId);
      const res = await startLesson(token, data.bai.ma_goc_id);
      setExitOpen(false);
      navigate(`/on-luyen/bai/${res.luot_id}`, { replace: true });
    } catch (err) {
      setError(err?.message || "Không mở lại được bài");
      setExitOpen(false);
    } finally {
      setBusy(false);
    }
  }

  // Phím 1–9 chọn phương án, Enter kiểm tra / tiếp tục
  useEffect(() => {
    function onKey(e) {
      if (!current || cards || exitOpen || e.target.tagName === "INPUT") return;
      if (e.key === "Enter") { e.preventDefault(); if (shown != null) next(); else if (pick != null) submit(); return; }
      const n = Number(e.key);
      if (shown == null && n >= 1 && n <= current.phuong_an.length && CHOICE.includes(current.cau_hoi.dang)) setPick(current.phuong_an[n - 1].id);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const shell = (body, footer) => (
    <div className="xg xc sl" data-theme={theme}>
      <div className="sl-wrap">
        <header className="sl-top">
          <button type="button" className="sl-x" aria-label="Thoát bài" onClick={() => (data?.trang_thai === "dang_lam" ? setExitOpen(true) : navigate(mapUrl))}>
            <Icon name="x" />
          </button>
          <span className="sl-progress" role="progressbar" aria-valuemin={0} aria-valuemax={items.length || 1} aria-valuenow={doneCount}
            aria-label="Tiến độ bài"><i style={{ width: `${items.length ? (100 * doneCount) / items.length : 0}%` }} /></span>
          {data && <span className="sl-tag">{SKILL[data.bai.ky_nang]} · {data.bai.ten_cap_do}</span>}
          {data && <span className="sp-stat sp-stat--energy"><Icon name="sprout" size={18} /><b>{data.nang_luong}/{data.nang_luong_toi_da}</b></span>}
        </header>
        <main className="sl-main">{body}</main>
      </div>
      {footer}
      {exitOpen && (
        <div className="xt-dialog sl-dialog" role="dialog" aria-modal="true" aria-labelledby="sl-exit">
          <div className="xt-dialog__box">
            <h2 id="sl-exit">Rời bài?</h2>
            <p>Câu đã kiểm tra được giữ lại; lần sau bấm ô này sẽ làm tiếp đúng bộ câu. Bỏ lượt thì tạo lượt mới, không hoàn năng lượng đã trừ.</p>
            <div className="sl-dialog__acts">
              <button type="button" className="xc-btn xc-btn--sm" onClick={() => setExitOpen(false)}>Làm tiếp</button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => navigate(mapUrl)}>Thoát, giữ bài</button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" disabled={busy} onClick={restart}>Bỏ lượt và làm lại</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (error && !data) return shell(<p role="alert">{error}</p>);
  if (!data) return shell(<p className="xc-muted">Đang tải bài...</p>);

  const meta = `${data.bai.loai === "cuoi_thua" ? "Kiểm tra cuối thửa" : `Bài ${data.bai.vi_tri}`} · ${data.bai.ten}`;

  if (data.trang_thai === "da_nop" && data.ket_qua) {
    const r = data.ket_qua;
    return shell(
      <div className={`sl-done${r.dat ? " is-pass" : ""}`}>
        <span className="sl-seal hz" aria-hidden="true">{r.dat ? "好" : "再"}</span>
        <p className="sl-meta">{data.bai.thua} · {meta}</p>
        <h1>{r.dat ? "Đạt rồi!" : "Chưa đạt"}</h1>
        <p className="sl-score"><b>{r.so_dung}/{r.tong}</b> câu đúng · cần đúng {r.tong}/{r.tong}</p>
        {r.dat && data.muc_dich !== "on_lai" && (
          <p className="sl-gain">{r.kn_nhan ? `+${r.kn_nhan} KN` : "Bài này đã nhận KN trước đó"} · {data.bai.loai === "cuoi_thua" ? "Đã thu hoạch thửa, mở thửa kế" : "Đã mở ô kế"}</p>
        )}
        {data.muc_dich === "on_lai" && <p className="sl-gain">Ôn lại: không tốn năng lượng, không cộng KN.</p>}
        {r.cau_can_on.length > 0 && (
          <div className="sl-review">
            <b>Câu cần ôn (đã lưu vào Sổ tay)</b>
            <ul>{r.cau_can_on.map((c) => <li key={c.thu_tu}><span>Câu {c.thu_tu}</span> {c.noi_dung}</li>)}</ul>
          </div>
        )}
        <div className="sl-done__acts">
          {r.dat ? (
            
            <button type="button" className="xc-btn" onClick={() => navigate(mapUrl)}>Về bản đồ <Icon name="arrow" /></button>
          ) : (
            <>
              <button type="button" className="xc-btn xc-btn--plain" onClick={() => navigate(mapUrl)}>Để sau</button>
              <button type="button" className="xc-btn" disabled={busy} onClick={restart}>Làm lại bài</button>
            </>
          )}
        </div>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  }

  if (cards) return shell(<FlashCards words={data.the_tu} onDone={() => setCards(false)} />);
  if (!current) return shell(<p className="xc-muted">Đang tổng kết...</p>);

  const q = current.cau_hoi;
  const fb = shown != null ? current.ket_qua : null;
  const chosen = fb ? current.tra_loi?.phuong_an_chon_id : pick;
  const right = fb?.dap_an_id;

  const footer = fb ? (
    <footer className={`sl-foot sl-foot--fb ${fb.dung ? "is-ok" : "is-bad"}`} role="status">
      <div className="sl-foot__in">
        <span className="sl-badge" aria-hidden="true">{fb.dung ? <Icon name="check" size={30} /> : "!"}</span>
        <div className="sl-fb">
          <b>{fb.dung ? "Chính xác!" : fb.bo_qua ? "Đã bỏ qua" : "Chưa đúng"}</b>
          {!fb.dung && right && (() => {
            const o = current.phuong_an.find((x) => x.id === right);
            return o && <p>Đáp án đúng: <strong><Option option={o} /></strong></p>;
          })()}
          {!fb.dung && fb.dap_an_chap_nhan?.length > 0 && <p>Đáp án: <strong className="hz">{fb.dap_an_chap_nhan.join(" / ")}</strong></p>}
          {fb.giai_thich && <p>{fb.giai_thich}</p>}
          {fb.loi_nghe && <p>Lời nghe: <span className="hz">{fb.loi_nghe}</span></p>}
          {fb.dich_nghia && <p className="sl-fb__vi">{fb.dich_nghia}</p>}
          {!fb.dung && (
            <p className="sl-fb__vi">
              {fb.nang_luong_tru ? `−1 năng lượng · còn ${data.nang_luong}/${data.nang_luong_toi_da}. ` : data.tieu_hao ? "Năng lượng đang 0, không trừ thêm. " : "Ôn lại không trừ năng lượng. "}
              Câu đã lưu vào Sổ tay.
            </p>
          )}
        </div>
                <div className="sl-acts">
          <button type="button" className="xx-open sl-ask" aria-pressed={chatOpen} onClick={() => setChatOpen(true)}>
            <img src={xiangFace} alt="" /> Hỏi Xiang
          </button>
          <button type="button" className="xc-btn" onClick={next} disabled={busy} autoFocus>Tiếp tục</button>
        </div>
      </div>
    </footer>
  ) : (
    <footer className="sl-foot">
      <div className="sl-foot__in">
        {error && <p role="alert">{error}</p>}
        <button type="button" className="xc-btn xc-btn--plain" onClick={() => submit(true)} disabled={busy}>Bỏ qua</button>
        <button type="button" className="xc-btn" onClick={() => submit(false)}
          disabled={busy || (CHOICE.includes(q.dang) ? pick == null : !text.trim())}>Kiểm tra</button>
      </div>
    </footer>
  );

  return shell(
    <div className="sl-q">
      <p className="sl-meta">{meta} · Câu {current.thu_tu}/{items.length}{data.muc_dich === "on_lai" ? " · Ôn lại" : ""}</p>
      <h1>{instruction(q, data.bai.ky_nang)}</h1>
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
          {current.phuong_an.map((o, i) => {
            let cls = "";
            if (fb) cls = o.id === right ? " is-right" : o.id === chosen ? " is-wrong" : " is-dim";
            else if (o.id === pick) cls = " is-picked";
            return (
              <button key={o.id} type="button" role="radio" aria-checked={o.id === chosen} className={`sl-opt${cls}`}
                disabled={!!fb} onClick={() => setPick(o.id)}>
                <kbd>{i + 1}</kbd><Option option={o} />
              </button>
            );
          })}
        </div>
      ) : (
         q.dang === "sap_xep" && current.phuong_an?.length ? (
          <SentenceBuilder key={q.id} pieces={current.phuong_an} extra={pickDistractors(items, current)} prompt={q.nghia_cau} value={text} onChange={setText} disabled={!!fb}
            answered={fb ? current.tra_loi?.van_ban || "" : null} />
        ) : (
          <input className="sl-input hz" value={fb ? current.tra_loi?.van_ban || "" : text} disabled={!!fb} maxLength={200}
            aria-label="Câu trả lời" onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && text.trim() && submit()} />
        )
      )}
      {fb && chatOpen && (
        <XiangChat key={q.id} luotId={Number(luotId)} cauHoiId={q.id} defaultOpen onClose={() => setChatOpen(false)} />
      )}
      {q.goi_y && !fb && q.dang !== "sap_xep" && <p className="sl-hint">Gợi ý: {q.goi_y}</p>}
    </div>,
    footer
  );
}
