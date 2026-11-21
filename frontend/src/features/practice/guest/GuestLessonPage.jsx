import { useEffect, useMemo, useState } from "react";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import Icon from "../../../shared/components/Icon.jsx";
import { useTheme } from "../../../shared/theme.js";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { ROLE } from "../../auth/utils/roles.js";
import "../../exam_catalog/styles/catalog.css";
import { mediaUrl } from "../../lecturer/utils/labels.js";
import "../../../layouts/staffShell.css";
import HanziText from "../../mock_test/components/HanziText.jsx";
import "../../mock_test/styles/mockTest.css";
import { skillSlug } from "../skills.js";
import "../styles/practice.css";
import { askGuestXiang, checkGuestAnswer, getGuestLesson } from "./guestPracticeApi.js";
import { GUEST_MAX_ENERGY, markResult, readGuest, spendEnergy } from "./guestProgress.js";
import { CHOICE, FlashCards, LATIN, Option, SKILL, instruction } from "./LessonParts.jsx";
import "./guestPractice.css";
import SentenceBuilder, { isPieceList, pickDistractors } from "../../../shared/components/SentenceBuilder.jsx";

// Lấy mảng tin nhắn từ lời gọi của XiangChat (dù gọi theo kiểu nào)
function pickMessages(args) {
  for (const a of args) {
    if (Array.isArray(a)) return a;
    if (a && typeof a === "object" && Array.isArray(a.tin_nhan)) return a.tin_nhan;
  }
  return [];
}

// Học thử 1 bài cho Khách: chấm ở máy chủ, không lưu vào tài khoản
export default function GuestLessonPage() {
  const { maGoc } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [theme] = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [cards, setCards] = useState(false);
  const [answers, setAnswers] = useState({}); // thu_tu → { tra_loi, ket_qua }
  const [pick, setPick] = useState(null);
  const [text, setText] = useState("");
  const [shown, setShown] = useState(null);
  const [busy, setBusy] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [energy, setEnergy] = useState(() => readGuest().nang_luong);
  const [consuming, setConsuming] = useState(true);
  const [finished, setFinished] = useState(false);
  const [round, setRound] = useState(0);

  useEffect(() => {
    if (user?.vai_tro === ROLE.HOC_VIEN) return undefined;
    const controller = new AbortController();
    setData(null); setAnswers({}); setShown(null); setPick(null); setText(""); setFinished(false); setError("");
    getGuestLesson(maGoc, controller.signal).then((d) => {
      const g = readGuest();
      const isReview = g.dat.includes(d.bai.ma_goc_id);
      if (!isReview && g.nang_luong <= 0) { setError("Hết năng lượng hôm nay. Đăng nhập để học tiếp và lưu tiến độ."); return; }
      setConsuming(!isReview);
      setEnergy(g.nang_luong);
      setData(d);
      setCards(d.the_tu.length > 0);
    }).catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài"));
    return () => controller.abort();
  }, [maGoc, round, user]);

  const items = data?.cau_hoi ?? [];
  const current = useMemo(() => {
    if (shown != null) return items.find((i) => i.thu_tu === shown);
    return items.find((i) => !answers[i.thu_tu]);
  }, [items, shown, answers]);
  const doneCount = Object.keys(answers).length;

  const mapUrl = location.state?.from
    || (data ? `/on-luyen/${skillSlug(data.bai.ky_nang)}?cap=${data.bai.cap_do_id}` : "/on-luyen");
  const login = () => navigate("/dang-nhap", { state: { from: mapUrl } });

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
      const res = await checkGuestAnswer(maGoc, body);
      let cut = 0;
      if (!res.ket_qua.dung && consuming) {
        cut = spendEnergy();
        setEnergy(readGuest().nang_luong);
      }
      setAnswers((a) => ({ ...a, [current.thu_tu]: { tra_loi: body, ket_qua: { ...res.ket_qua, nang_luong_tru: cut } } }));
      setShown(current.thu_tu);
    } catch (err) {
      setError(err?.message || "Chưa kiểm tra được, hãy thử lại");
    } finally {
      setBusy(false);
    }
  }

  function next() {
    setPick(null); setText(""); setShown(null); setChatOpen(false);
    if (Object.keys(answers).length === items.length) {
      const passed = items.every((i) => answers[i.thu_tu]?.ket_qua.dung);
      markResult(data.bai.ma_goc_id, passed);
      setFinished(true);
    }
  }

  function restart() {
    setExitOpen(false);
    if (readGuest().nang_luong <= 0 && consuming) { setError("Hết năng lượng hôm nay. Đăng nhập để học tiếp và lưu tiến độ."); return; }
    setRound((r) => r + 1);
  }

  const guestAsk = (...args) => {
    const a = answers[current?.thu_tu];
    return askGuestXiang({
      bai_ma_goc_id: Number(maGoc), cau_hoi_id: current.cau_hoi.id,
      phuong_an_chon_id: a?.tra_loi.phuong_an_chon_id ?? null, van_ban: a?.tra_loi.van_ban ?? null,
      tin_nhan: pickMessages(args),
    });
  };

  // Phím 1–9 chọn phương án, Enter kiểm tra / tiếp tục
  useEffect(() => {
    function onKey(e) {
      if (!current || cards || exitOpen || finished || ["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === "Enter") { e.preventDefault(); if (shown != null) next(); else if (pick != null) submit(); return; }
      const n = Number(e.key);
      if (shown == null && n >= 1 && n <= current.phuong_an.length && CHOICE.includes(current.cau_hoi.dang)) setPick(current.phuong_an[n - 1].id);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (user?.vai_tro === ROLE.HOC_VIEN) return <Navigate to="/hoc-vien/on-luyen" replace />;

  const inProgress = data && !finished && doneCount > 0;
  const shell = (body, footer) => (
    <div className="xg xc sl" data-theme={theme}>
      <div className="sl-wrap">
        <header className="sl-top">
          <button type="button" className="sl-x" aria-label="Thoát bài" onClick={() => (inProgress ? setExitOpen(true) : navigate(mapUrl))}>
            <Icon name="x" />
          </button>
          <span className="sl-progress" role="progressbar" aria-valuemin={0} aria-valuemax={items.length || 1} aria-valuenow={doneCount}
            aria-label="Tiến độ bài"><i style={{ width: `${items.length ? (100 * doneCount) / items.length : 0}%` }} /></span>
          {data && <span className="sl-tag">Học thử · {SKILL[data.bai.ky_nang]} · {data.bai.ten_cap_do}</span>}
          <span className="sp-stat sp-stat--energy"><Icon name="sprout" size={18} /><b>{energy}/{GUEST_MAX_ENERGY}</b></span>
        </header>
        <main className="sl-main">{body}</main>
      </div>
      {footer}
      {exitOpen && (
        <div className="xt-dialog sl-dialog" role="dialog" aria-modal="true" aria-labelledby="sl-exit">
          <div className="xt-dialog__box">
            <h2 id="sl-exit">Rời bài?</h2>
            <p>Bạn đang học thử nên bài làm dở không được giữ lại. Năng lượng đã trừ không được hoàn.</p>
            <div className="sl-dialog__acts">
              <button type="button" className="xc-btn xc-btn--sm" onClick={() => setExitOpen(false)}>Làm tiếp</button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => navigate(mapUrl)}>Thoát</button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={login}>Đăng nhập để lưu</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (error && !data) {
    return shell(
      <div className="sl-done">
        <p role="alert">{error}</p>
        <div className="sl-done__acts">
          <button type="button" className="xc-btn xc-btn--plain" onClick={() => navigate(mapUrl)}>Về bản đồ</button>
          <button type="button" className="xc-btn" onClick={login}>Đăng nhập</button>
        </div>
      </div>
    );
  }
  if (!data) return shell(<p className="xc-muted">Đang tải bài...</p>);

  const meta = `${data.bai.loai === "cuoi_thua" ? "Kiểm tra cuối thửa" : `Bài ${data.bai.vi_tri}`} · ${data.bai.ten}`;

  if (finished) {
    const right = items.filter((i) => answers[i.thu_tu]?.ket_qua.dung).length;
    const passed = right === items.length;
    const wrong = items.filter((i) => !answers[i.thu_tu]?.ket_qua.dung);
    return shell(
      <div className={`sl-done${passed ? " is-pass" : ""}`}>
        <span className="sl-seal hz" aria-hidden="true">{passed ? "好" : "再"}</span>
        <p className="sl-meta">{data.bai.thua} · {meta}</p>
        <h1>{passed ? "Đạt rồi!" : "Chưa đạt"}</h1>
        <p className="sl-score"><b>{right}/{items.length}</b> câu đúng · cần đúng {items.length}/{items.length}</p>
        {passed && <p className="sl-gain">{data.bai.loai === "cuoi_thua" ? "Đã thu hoạch thửa, mở thửa kế" : "Đã mở ô kế"} (học thử)</p>}
        <p className="sl-guest">Kết quả không được lưu vì bạn chưa đăng nhập. Đăng nhập để lưu tiến độ, nhận KN và ghi câu sai vào Sổ tay.</p>
        {wrong.length > 0 && (
          <div className="sl-review">
            <b>Câu cần ôn</b>
            <ul>{wrong.map((c) => <li key={c.thu_tu}><span>Câu {c.thu_tu}</span> {c.cau_hoi.noi_dung}</li>)}</ul>
          </div>
        )}
        <div className="sl-done__acts">
          <button type="button" className="xc-btn xc-btn--plain" onClick={() => navigate(mapUrl)}>Về bản đồ</button>
          {!passed && <button type="button" className="xc-btn xc-btn--plain" onClick={restart}>Làm lại bài</button>}
          <button type="button" className="xc-btn" onClick={login}>Đăng nhập để lưu</button>
        </div>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  }

  if (cards) return shell(<FlashCards words={data.the_tu} onDone={() => setCards(false)} />);
  if (!current) return shell(<p className="xc-muted">Đang tổng kết...</p>);

  const q = current.cau_hoi;
  const done = shown != null ? answers[current.thu_tu] : null;
  const fb = done?.ket_qua ?? null;
  const chosen = fb ? done.tra_loi.phuong_an_chon_id : pick;
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
              {fb.nang_luong_tru ? `−1 năng lượng · còn ${energy}/${GUEST_MAX_ENERGY}.` : consuming ? "Năng lượng đang 0, không trừ thêm." : "Ôn lại không trừ năng lượng."}
            </p>
          )}
        </div>
        <div className="sl-acts">
          {!chatOpen && (
            <button type="button" className="xx-open sl-ask" onClick={() => setChatOpen(true)}>
              <img src={xiangFace} alt="" />Hỏi Xiang
            </button>
          )}
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
      <p className="sl-meta">{meta} · Câu {current.thu_tu}/{items.length} · Học thử</p>
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
            answered={fb ? done.tra_loi.van_ban || "" : null} />
        ) : (
          <input className="sl-input hz" value={fb ? done.tra_loi.van_ban || "" : text} disabled={!!fb} maxLength={200}
            aria-label="Câu trả lời" onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && text.trim() && submit()} />
        )
      )}
      {q.goi_y && !fb && q.dang !== "sap_xep" && <p className="sl-hint">Gợi ý: {q.goi_y}</p>}
      {fb && chatOpen && (
        <XiangChat key={q.id} luotId={null} cauHoiId={q.id} defaultOpen onClose={() => setChatOpen(false)} ask={guestAsk} />
      )}
    </div>,
    footer
  );
}
