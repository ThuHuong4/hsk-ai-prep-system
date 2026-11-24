import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import "../../../layouts/staffShell.css";
import HanziText from "../../../shared/components/HanziText.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { CHOICE, LATIN, Option, SKILL, instruction } from "../../../shared/components/LessonParts.jsx";
import SentenceBuilder, { isPieceList, pickDistractors } from "../../../shared/components/SentenceBuilder.jsx";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import { mediaUrl } from "../../../shared/utils/format.js";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import "../../mock_test/styles/mockTest.css";
import "../../practice/styles/practice.css";
import {
  abandonNotebookReview,
  askNotebookXiang,
  checkNotebookAnswer,
  getNotebookReview,
  markNotebookSolutionViewed,
} from "../api/notebookApi.js";
import DailyMissions from "../components/DailyMissions.jsx";
import "../styles/notebook.css";

const STATE = {
  can_on: "Cần ôn lại thêm",
  cho_on_lai: "Chờ ôn lại · hẹn ngày mai",
  da_cung_co: "Đã củng cố vững",
};
const BACK = "/hoc-vien/so-tay-cau-sai";

export default function NotebookReviewPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [pick, setPick] = useState(null);
  const [text, setText] = useState("");
  const [shown, setShown] = useState(null);
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [busy, setBusy] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getNotebookReview(token, luotId, controller.signal)
      .then(setData)
      .catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được lượt ôn"));
    return () => controller.abort();
  }, [token, luotId]);

  const items = data?.cau_hoi ?? [];
  const current = useMemo(
    () => (shown != null ? items.find((i) => i.thu_tu === shown) : items.find((i) => !i.ket_qua)),
    [items, shown]
  );
  const doneCount = items.filter((i) => i.ket_qua).length;
  const finished = data && doneCount === items.length && shown == null;

  async function submit(skip = false) {
    if (!current || busy) return;
    const q = current.cau_hoi;
    const body = { cau_hoi_id: q.id, phuong_an_chon_id: null, van_ban: null };
    if (!skip) {
      if (CHOICE.includes(q.dang)) body.phuong_an_chon_id = pick;
      else body.van_ban = text.trim() || null;
    }
    setBusy(true);
    setError("");
    setRevealAnswer(false);
    try {
      const res = await checkNotebookAnswer(token, luotId, body);
      setData((d) => ({
        ...d,
        cau_hoi: d.cau_hoi.map((i) =>
          i.thu_tu === current.thu_tu ? { ...i, tra_loi: body, ket_qua: res.ket_qua } : i
        ),
        ket_qua: res.ket_thuc
          ? { ...(d.ket_qua || {}), nang_luong_hoi: res.nang_luong_hoi || 0 }
          : d.ket_qua,
      }));
      if (res.ket_thuc) {
        window.dispatchEvent(new Event("xianglingo:stats"));
      }
      if (skip) {
        setPick(null);
        setText("");
        setShown(null);
        setChatOpen(false);
        return;
      }
      setShown(current.thu_tu);
    } catch (err) {
      setError(err?.message || "Chưa kiểm tra được, hãy thử lại");
    } finally {
      setBusy(false);
    }
  }

  function handleRevealAnswer() {
    setRevealAnswer(true);
    if (current?.cau_hoi?.id) {
      markNotebookSolutionViewed(token, luotId, current.cau_hoi.id).catch(() => {});
    }
  }

  function next() {
    setPick(null);
    setText("");
    setShown(null);
    setRevealAnswer(false);
    setChatOpen(false);
  }

  async function leave(abandon) {
    if (abandon) {
      try {
        await abandonNotebookReview(token, luotId);
      } catch {
        /* vẫn thoát */
      }
    }
    navigate(BACK);
  }

  useEffect(() => {
    function onKey(e) {
      if (!current || exitOpen || ["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === "Enter") {
        e.preventDefault();
        if (shown != null) next();
        else if (pick != null) submit(false);
        return;
      }
      const n = Number(e.key);
      if (shown == null && n >= 1 && n <= current.phuong_an.length && CHOICE.includes(current.cau_hoi.dang)) {
        setPick(current.phuong_an[n - 1].id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const shell = (body, footer) => (
    <div className="xg xc sl" data-theme={theme}>
      <div className="sl-wrap">
        <header className="sl-top">
          <button
            type="button"
            className="sl-x"
            aria-label="Thoát"
            onClick={() => (data && !finished && doneCount > 0 ? setExitOpen(true) : navigate(BACK))}
          >
            <Icon name="x" />
          </button>
          <span
            className="sl-progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={items.length || 1}
            aria-valuenow={doneCount}
            aria-label="Tiến độ lượt ôn"
          >
            <i style={{ width: `${items.length ? (100 * doneCount) / items.length : 0}%` }} />
          </span>
          <span className="sl-tag">
            <Icon name="book" size={14} /> Ôn Sổ tay · không tốn năng lượng
          </span>
        </header>
        <main className="sl-main">{body}</main>
      </div>
      {footer}
      {exitOpen && (
        <div className="xt-dialog sl-dialog" role="dialog" aria-modal="true" aria-labelledby="nb-exit">
          <div className="xt-dialog__box">
            <h2 id="nb-exit">Rời lượt ôn?</h2>
            <p>Câu đã trả lời vẫn được tính. Lần sau bấm Ôn ngay sẽ làm tiếp lượt này.</p>
            <div className="sl-dialog__acts">
              <button type="button" className="xc-btn xc-btn--sm" onClick={() => setExitOpen(false)}>
                Ôn tiếp
              </button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => leave(false)}>
                Thoát, giữ lượt
              </button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => leave(true)}>
                Kết thúc lượt
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (error && !data) return shell(<p role="alert">{error}</p>);
  if (!data) return shell(<p className="xc-muted">Đang tải lượt ôn...</p>);

  if (finished) {
    const right = items.filter((i) => i.ket_qua.dung).length;
    const firm = items.filter((i) => i.ket_qua.dung && i.ket_qua.trang_thai_moi === "da_cung_co").length;
    const pct = items.length ? Math.round((100 * right) / items.length) : 0;
    const recovered = data.ket_qua?.nang_luong_hoi || 0;
    return shell(
      <div className="sl-done is-pass">
        <span className="sl-seal hz" aria-hidden="true">
          复
        </span>
        <p className="sl-meta">Ôn Sổ tay · {items.length} câu</p>
        <h1>Xong lượt ôn!</h1>
        <p className="sl-score">
          <b>
            {right}/{items.length}
          </b>{" "}
          câu đúng ({pct}%){firm ? ` · ${firm} câu đã củng cố (+${firm} KN)` : ""}
        </p>
        {recovered > 0 ? (
          <p className="sl-gain">🌱 +{recovered} năng lượng hồi phục (đạt từ 80% câu đúng)!</p>
        ) : pct < 80 ? (
          <p className="sl-note" style={{ color: "var(--coral-ink)", fontWeight: 700 }}>
            Đạt từ 80% câu đúng trong một lượt ôn Sổ tay sẽ tự hồi ngay +1 🌱 khi bình năng lượng chưa đầy.
          </p>
        ) : null}
        <p className="sl-note">Câu sai giữ ở trạng thái Cần ôn; câu đúng lần đầu được hẹn ôn lại ngày mai.</p>
        <div className="nb-result-missions">
          <DailyMissions compact />
        </div>
        <div className="sl-done__acts">
          <button type="button" className="xc-btn xc-btn--plain" onClick={() => navigate(BACK)}>
            Về Sổ tay
          </button>
          <button type="button" className="xc-btn" onClick={() => navigate("/hoc-vien/on-luyen")}>
            Quay lại Ôn luyện
          </button>
        </div>
      </div>
    );
  }

  if (!current) return shell(<p className="xc-muted">Đang tổng kết...</p>);
  const q = current.cau_hoi;
  const fb = shown != null ? current.ket_qua : null;
  const chosen = fb ? current.tra_loi?.phuong_an_chon_id : pick;
  const right = fb?.dap_an_id;
  const hasAnswer = CHOICE.includes(q.dang) ? pick != null : Boolean(text.trim());

  const footer = fb ? (
    <footer className={`sl-foot sl-foot--fb ${fb.dung ? "is-ok" : "is-bad"}`} role="status">
      <div className="sl-foot__in">
        <span className="sl-badge" aria-hidden="true">
          {fb.dung ? <Icon name="check" size={30} /> : "!"}
        </span>
        <div className="sl-fb">
          <b>{fb.dung ? "Chính xác!" : "Chưa đúng"}</b>
          {fb.dung ? (
            <>
              {fb.giai_thich && <p>{fb.giai_thich}</p>}
              {fb.dich_nghia && <p className="sl-fb__vi">{fb.dich_nghia}</p>}
            </>
          ) : (
            <>
              {fb.goi_mo && <p>{fb.goi_mo}</p>}
              {!revealAnswer ? (
                <button type="button" className="sl-fb-link" onClick={handleRevealAnswer}>
                  Xem đáp án & lời giải
                </button>
              ) : (
                <>
                  {right &&
                    (() => {
                      const o = current.phuong_an.find((x) => x.id === right);
                      return (
                        o && (
                          <p>
                            Đáp án đúng: <strong><Option option={o} /></strong>
                          </p>
                        )
                      );
                    })()}
                  {fb.dap_an_chap_nhan?.length > 0 && (
                    <p>
                      Đáp án: <strong className="hz">{fb.dap_an_chap_nhan.join(" / ")}</strong>
                    </p>
                  )}
                  {fb.giai_thich && <p>{fb.giai_thich}</p>}
                  {fb.dich_nghia && <p className="sl-fb__vi">{fb.dich_nghia}</p>}
                </>
              )}
            </>
          )}
          {fb.trang_thai_moi && (
            <p className="sl-fb__vi">
              Sổ tay: {STATE[fb.trang_thai_moi]}
              {fb.dung && fb.trang_thai_moi === "da_cung_co" ? " · +1 KN" : ""}
            </p>
          )}
        </div>
        <div className="sl-acts">
          {!fb.bo_qua && (
            <button type="button" className="xx-open sl-ask" aria-pressed={chatOpen} onClick={() => setChatOpen((v) => !v)}>
              <img src={xiangFace} alt="" /> Hỏi Xiang
            </button>
          )}
          <button type="button" className="xc-btn" onClick={next} autoFocus>
            Tiếp tục
          </button>
        </div>
      </div>
    </footer>
  ) : (
    <footer className="sl-foot">
      <div className="sl-foot__in">
        {error && <p role="alert">{error}</p>}
        <button type="button" className="xc-btn xc-btn--plain" onClick={() => submit(true)} disabled={busy}>
          Bỏ qua
        </button>
        <button type="button" className="xc-btn" onClick={() => submit(false)} disabled={busy || !hasAnswer}>
          Kiểm tra
        </button>
      </div>
    </footer>
  );

  return shell(
    <div className="sl-q">
      <p className="sl-meta">
        Câu {current.thu_tu}/{items.length} · {SKILL[q.ky_nang]}
      </p>
      <h1>{instruction(q, q.ky_nang)}</h1>
      {current.ngu_lieu && (current.ngu_lieu.noi_dung || current.ngu_lieu.tep_hinh) && (
        <div className="sl-passage">
          {current.ngu_lieu.tep_hinh && <img src={mediaUrl(current.ngu_lieu.tep_hinh)} alt="" />}
          {current.ngu_lieu.noi_dung && <HanziText text={current.ngu_lieu.noi_dung} pinyin={current.ngu_lieu.pinyin} />}
        </div>
      )}
      {(q.tep_audio || current.ngu_lieu?.tep_audio) && (
        <audio className="sl-audio" controls src={mediaUrl(q.tep_audio || current.ngu_lieu.tep_audio)} />
      )}
      {((q.noi_dung && !isPieceList(q.noi_dung)) || q.tep_hinh) && (
        <div className={`sl-stem${q.noi_dung && !LATIN.test(q.noi_dung) && q.noi_dung.length <= 4 ? " sl-stem--word" : ""}`}>
          {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} />}
          {q.noi_dung &&
            !isPieceList(q.noi_dung) &&
            (LATIN.test(q.noi_dung) ? <p>{q.noi_dung}</p> : <HanziText text={q.noi_dung} pinyin={q.pinyin} />)}
        </div>
      )}
      {CHOICE.includes(q.dang) ? (
        <div className={`sl-opts${current.phuong_an.some((o) => o.tep_hinh) ? " sl-opts--img" : ""}`} role="radiogroup" aria-label="Phương án">
          {current.phuong_an.map((o, i) => {
            let cls = "";
            if (fb) {
              if (fb.dung || revealAnswer) cls = o.id === right ? " is-right" : o.id === chosen ? " is-wrong" : " is-dim";
              else cls = o.id === chosen ? " is-wrong" : "";
            } else if (o.id === pick) {
              cls = " is-picked";
            }
            return (
              <button
                key={o.id}
                type="button"
                role="radio"
                aria-checked={o.id === chosen}
                className={`sl-opt${cls}`}
                disabled={Boolean(fb) || busy}
                onClick={() => setPick(o.id)}
              >
                <kbd>{i + 1}</kbd>
                <Option option={o} />
              </button>
            );
          })}
        </div>
      ) : q.dang === "sap_xep" && current.phuong_an?.length ? (
        <SentenceBuilder
          key={q.id}
          pieces={current.phuong_an}
          extra={pickDistractors(items, current)}
          prompt={q.nghia_cau}
          value={text}
          onChange={setText}
          disabled={Boolean(fb) || busy}
          answered={fb ? current.tra_loi?.van_ban || "" : null}
        />
      ) : (
        <input
          className="sl-input hz"
          value={fb ? current.tra_loi?.van_ban || "" : text}
          disabled={Boolean(fb) || busy}
          maxLength={200}
          aria-label="Câu trả lời"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && text.trim() && submit(false)}
        />
      )}
      {q.goi_y && !fb && q.dang !== "sap_xep" && <p className="sl-hint">Gợi ý: {q.goi_y}</p>}
      {fb && !fb.bo_qua && chatOpen && (
        <XiangChat
          key={q.id}
          luotId={Number(luotId)}
          cauHoiId={q.id}
          isCorrect={fb.dung}
          sendFn={(_, cauId, msgs) => askNotebookXiang(token, Number(luotId), { cau_hoi_id: cauId, tin_nhan: msgs })}
          defaultOpen
          onClose={() => setChatOpen(false)}
        />
      )}
    </div>,
    footer
  );
}
