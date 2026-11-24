/**
 * Trạm thi HSK trên máy tính (`ExamSessionPage.jsx` — chuẩn giao diện & quy chế `HSK机考 / ChineseTest Client`, AT18–AT22, AT41, AT43):
 * - Bố cục Trạm thi Toàn màn hình (`100dvh`):
 *     + Thanh đỉnh chuẩn máy thi: Thẻ thí sinh (Họ tên, SBD, trạng thái lưu) · Tiến trình phần thi một chiều · Chỉnh cỡ chữ `A / A+ / A++` · Đồng hồ đếm ngược · 1 nút Nộp phần / Nộp bài duy nhất.
 *     + Cột TRÁI cố định: Bảng số câu (`题号导航`) chia theo `一、听力 · 二、阅读 · 三、书写`, khóa chặt các phần đã qua / chưa mở (`严禁跨区`).
 *     + Khung CHÍNH bên phải: Thanh băng Nghe tự động phát không tua ở mép trên · Vùng câu hỏi chính diện (nhóm câu đọc hiểu/ghép từ tự động chia 2 cột Trái ngữ liệu – Phải câu hỏi; câu mẫu `例如` thu gọn mở 1 chạm để không ép nhỏ câu thi thật) · Thanh điều hướng `← Câu trước · ⚑ Đánh dấu · Câu tiếp theo →` ghim cố định cạnh dưới.
 * - Bảo mật cấp độ: giữ kín tên cấp HSK trong suốt quá trình thi (A2).
 * - Phím tắt chuẩn máy thi: `←` / `→` chuyển câu trong phần đang mở (`AT43`), `1–6` / `A–F` chọn phương án, `M` gắn cờ `⚑` (`AT22` tắt khi gõ chữ).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useNavigationType, useParams } from "react-router-dom";

import { mediaUrl } from "../../../shared/utils/format.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { advanceExamSection, getAttempt, saveAnswer, submitAttempt } from "../api/mockTestApi.js";
import { GroupBlock, SingleRow } from "../components/ExamPaper.jsx";
import ExamShell from "../components/ExamShell.jsx";
import ProctoredAudioPlayer from "../components/ProctoredAudioPlayer.jsx";
import QuestionNav from "../components/QuestionNav.jsx";
import "../styles/examFlags.css";
import { buildPaper, formatClock } from "../utils/paper.js";

const flagKey = (id) => `xianglingo-exam-flags-${id}`;
const strikeKey = (id) => `xianglingo-exam-strikes-${id}`;
const MAX_FOCUS_STRIKES = 3;
const FONT_KEY = "xianglingo-exam-font";

function readFlags(id) {
  try {
    return new Set(JSON.parse(localStorage.getItem(flagKey(id)) || "[]"));
  } catch {
    return new Set();
  }
}

function readStrikes(id) {
  try {
    return Math.max(0, Number(localStorage.getItem(strikeKey(id)) || 0));
  } catch {
    return 0;
  }
}

function readFontScale() {
  try {
    const v = localStorage.getItem(FONT_KEY);
    return ["md", "lg", "xl"].includes(v) ? v : "md";
  } catch {
    return "md";
  }
}

function clearSessionAudioKeys(id) {
  try {
    const prefix = `xianglingo-audio-${id}-`;
    for (let i = sessionStorage.length - 1; i >= 0; i -= 1) {
      const k = sessionStorage.key(i);
      if (k && k.startsWith(prefix)) sessionStorage.removeItem(k);
    }
  } catch {
    /* bỏ qua */
  }
}

export default function ExamSessionPage() {
  const { luotId } = useParams();
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const navType = useNavigationType();
  const [data, setData] = useState(null);
  const [items, setItems] = useState([]);
  const [activeSkill, setActiveSkill] = useState(null);
  const [lockedSkills, setLockedSkills] = useState([]);
  const [remaining, setRemaining] = useState(null);
  const [saving, setSaving] = useState(0);
  const [error, setError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [sectionConfirmOpen, setSectionConfirmOpen] = useState(false);
  const [advancingSection, setAdvancingSection] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [flags, setFlags] = useState(() => readFlags(luotId));
  const [current, setCurrent] = useState(null);
  const [showExample, setShowExample] = useState(false);
  const [mobilePaletteOpen, setMobilePaletteOpen] = useState(false);
  const [lowWarnDismissed, setLowWarnDismissed] = useState(false);
  const [listeningTapeEnded, setListeningTapeEnded] = useState(false);
  const [fontScale, setFontScale] = useState(readFontScale);
  const [focusStrikes, setFocusStrikes] = useState(() => readStrikes(luotId));
  const [proctorModalOpen, setProctorModalOpen] = useState(false);
  const [backBlockedOpen, setBackBlockedOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(() => Boolean(document.fullscreenElement));

  const deadline = useRef(null);
  const submittedRef = useRef(false);
  const restoredInitRef = useRef(false);
  const canvasRef = useRef(null);

  const exitFullscreenSafe = useCallback(() => {
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  }, []);

  const goResult = useCallback(async () => {
    exitFullscreenSafe();
    // Gỡ bỏ mốc khóa Back tạm thời trong lịch sử trước khi thay thế bằng trang Kết quả
    // để từ trang Kết quả bấm Back về thẳng Phòng chờ, và từ Phòng chờ bấm Back về thẳng Trang chủ!
    if (window.history.state?.hskExamGuard) {
      await new Promise((resolve) => {
        const done = () => {
          window.removeEventListener("popstate", done);
          resolve();
        };
        window.addEventListener("popstate", done, { once: true });
        window.history.back();
        setTimeout(done, 120);
      });
    }
    navigate(`/thi-thu/ket-qua/${luotId}`, { replace: true, state: { fromLobby: true } });
  }, [exitFullscreenSafe, navigate, luotId]);

  function handleFontChange(nextScale) {
    setFontScale(nextScale);
    try {
      localStorage.setItem(FONT_KEY, nextScale);
    } catch {
      /* bỏ qua */
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    getAttempt(token, luotId, controller.signal)
      .then((d) => {
        if (d.trang_thai !== "dang_lam") {
          // Nếu thí sinh từ trang Kết quả bấm nút Back (←) của trình duyệt lùi về URL phòng thi đã nộp,
          // đưa thẳng về Phòng chờ thi thử thay vì đẩy ngược lại trang Kết quả gây kẹt nút Back!
          if (navType === "POP") {
            exitFullscreenSafe();
            navigate("/hoc-vien/thi-thu", { replace: true });
          } else {
            goResult();
          }
          return;
        }
        setData(d);
        setItems(d.cau_hoi);
        setActiveSkill(d.ky_nang_hien_tai || null);
        setLockedSkills(d.cac_phan_da_khoa || []);
        deadline.current = Date.now() + d.con_lai_giay * 1000;
        setRemaining(d.con_lai_giay);
      })
      .catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài thi"));
    return () => controller.abort();
  }, [token, luotId, goResult, navType, exitFullscreenSafe, navigate]);

  const submit = useCallback(
    async (isTimeout = false, isViolation = false) => {
      if (submittedRef.current) return;
      submittedRef.current = true;
      if (isTimeout || isViolation) {
        setConfirmOpen(false);
        setSectionConfirmOpen(false);
        setProctorModalOpen(false);
      }
      setSubmitting(true);
      setError("");
      try {
        await submitAttempt(token, luotId, isTimeout, isViolation);
        try {
          localStorage.removeItem(flagKey(luotId));
          localStorage.removeItem(strikeKey(luotId));
        } catch {
          /* bỏ qua */
        }
        clearSessionAudioKeys(luotId);
        goResult();
      } catch (err) {
        submittedRef.current = false;
        setSubmitting(false);
        setConfirmOpen(false);
        if (isTimeout || isViolation) {
          // Đảm bảo thu bài tự động khi hết giờ 00:00 hoặc vi phạm quy chế 3 lần không bị kẹt bởi trễ mạng
          setTimeout(() => submit(isTimeout, isViolation), 2000);
          return;
        }
        setError(err?.message || "Nộp bài thất bại, hãy thử lại");
      }
    },
    [token, luotId, goResult]
  );

  // AT20, AT41: Đồng hồ chạm 00:00 -> tự động nộp ngay phần đã làm, không hiện hộp xác nhận
  useEffect(() => {
    if (remaining === null) return undefined;
    const timer = setInterval(() => {
      const left = Math.max(0, Math.round((deadline.current - Date.now()) / 1000));
      setRemaining(left);
      if (left <= 0) {
        clearInterval(timer);
        submit(true);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [remaining === null, submit]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleFlag = useCallback(
    (no) => {
      if (!no) return;
      setFlags((prev) => {
        const next = new Set(prev);
        if (next.has(no)) next.delete(no);
        else next.add(no);
        try {
          localStorage.setItem(flagKey(luotId), JSON.stringify([...next]));
        } catch {
          /* bỏ qua */
        }
        return next;
      });
    },
    [luotId]
  );

  // 1. Chặn đóng Tab / cửa sổ nhầm trong suốt ca thi đang diễn ra
  useEffect(() => {
    if (!data) return undefined;
    const handler = (e) => {
      if (!submittedRef.current) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [data]);

  // 2. Chặn bấm nhầm nút Back (←) trình duyệt làm văng khỏi phòng thi / ngắt băng Nghe (chỉ đẩy tối đa 1 mốc bảo vệ)
  useEffect(() => {
    if (!data) return undefined;
    if (!window.history.state?.hskExamGuard) {
      window.history.pushState({ hskExamGuard: true }, "", window.location.href);
    }
    const onPopState = () => {
      if (submittedRef.current) return;
      window.history.pushState({ hskExamGuard: true }, "", window.location.href);
      setBackBlockedOpen(true);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [data]);

  // 3. Theo dõi trạng thái Toàn màn hình (`Fullscreen`)
  useEffect(() => {
    const onFsChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  // 4. Giám sát chuyển Tab / thu nhỏ màn hình thi (`切屏监控` — cảnh báo 1/3, 2/3, lần 3/3 tự thu bài)
  useEffect(() => {
    if (!data) return undefined;
    let armed = false;
    const armTimer = setTimeout(() => {
      armed = true;
    }, 1200);

    const onVisibility = () => {
      if (!armed || submittedRef.current) return;
      if (document.visibilityState === "hidden") {
        setFocusStrikes((prev) => {
          const next = prev + 1;
          try {
            localStorage.setItem(strikeKey(luotId), String(next));
          } catch {
            /* bỏ qua */
          }
          if (next >= MAX_FOCUS_STRIKES) {
            submit(false, true);
          } else {
            setProctorModalOpen(true);
          }
          return next;
        });
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearTimeout(armTimer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [data, luotId, submit]);

  const persist = useCallback(
    async (item, patch) => {
      const previous = item.tra_loi;
      setItems((list) =>
        list.map((i) => (i.cau_hoi.id === item.cau_hoi.id ? { ...i, tra_loi: { ...i.tra_loi, ...patch } } : i))
      );
      setSaving((n) => n + 1);
      setError("");
      try {
        const res = await saveAnswer(token, luotId, { cau_hoi_id: item.cau_hoi.id, ...patch, vi_tri: item.so_cau });
        deadline.current = Date.now() + res.con_lai_giay * 1000;
      } catch (err) {
        setItems((list) => list.map((i) => (i.cau_hoi.id === item.cau_hoi.id ? { ...i, tra_loi: previous } : i)));
        if (err?.status === 409) {
          goResult();
          return;
        }
        setError(err?.message || "Chưa lưu được câu trả lời, hãy chọn lại");
      } finally {
        setSaving((n) => n - 1);
      }
    },
    [token, luotId, goResult]
  );

  const onPick = useCallback(
    (item, optionId) => {
      // Chuẩn nút Radio phần mềm HSK机考: bấm lại phương án đang chọn vẫn giữ nguyên (không tự xóa thành câu trống)
      if (item.tra_loi?.phuong_an_chon_id === optionId) return;
      persist(item, { phuong_an_chon_id: optionId, van_ban: null });
    },
    [persist]
  );

  const onText = useCallback(
    (item, value) => {
      persist(item, { phuong_an_chon_id: null, van_ban: value || null });
    },
    [persist]
  );

  const sections = useMemo(() => buildPaper(items), [items]);
  const scored = useMemo(() => items.filter((i) => !i.la_cau_vi_du), [items]);

  // Gom từng Phần thi thành danh sách Khối câu HSK iBT; câu ví dụ `例如` gắn theo Phần để bật/tắt 1 chạm mà không ép nhỏ câu thật
  const ibtBlocks = useMemo(() => {
    const list = [];
    for (const sec of sections) {
      for (const part of sec.parts) {
        const partExamples = part.blocks.filter((blk) => blk.items.every((x) => x.la_cau_vi_du));
        for (const blk of part.blocks) {
          const scoredInBlk = blk.items.filter((x) => !x.la_cau_vi_du);
          if (scoredInBlk.length === 0) continue;
          list.push({
            ky_nang: sec.ky_nang,
            phanKey: `${sec.ky_nang}-${part.phan}`,
            sectionTitle: sec.title,
            sectionLabel: sec.label,
            partTitle: part.title,
            partFrom: part.from,
            partTo: part.to,
            block: blk,
            examples: partExamples,
            questionNumbers: scoredInBlk.map((x) => x.so_cau),
          });
        }
      }
    }
    return list;
  }, [sections]);

  // Chỉ mở các khối câu thuộc đúng phần kỹ năng hiện tại (`严禁跨区`)
  const sectionBlocks = useMemo(
    () => (activeSkill ? ibtBlocks.filter((b) => b.ky_nang === activeSkill) : ibtBlocks),
    [ibtBlocks, activeSkill]
  );

  const activeSecScored = useMemo(
    () => (activeSkill ? scored.filter((i) => i.ky_nang === activeSkill) : scored),
    [scored, activeSkill]
  );

  const curSecIdx = useMemo(
    () => (activeSkill ? sections.findIndex((s) => s.ky_nang === activeSkill) : 0),
    [sections, activeSkill]
  );
  const activeSectionMeta = curSecIdx >= 0 ? sections[curSecIdx] : sections[0] || null;
  const nextSectionMeta = curSecIdx >= 0 && curSecIdx < sections.length - 1 ? sections[curSecIdx + 1] : null;

  // Khôi phục đúng câu đang làm trong phần đang mở khi mở đề / F5 (AT18)
  useEffect(() => {
    if (!data || restoredInitRef.current || activeSecScored.length === 0) return;
    restoredInitRef.current = true;
    const savedPos = data.vi_tri_hien_tai;
    const validTarget = activeSecScored.some((i) => i.so_cau === savedPos) ? savedPos : activeSecScored[0].so_cau;
    setCurrent(validTarget);
  }, [data, activeSecScored]);

  const activeBlockIdx = useMemo(() => {
    if (!sectionBlocks.length) return 0;
    if (current != null) {
      const idx = sectionBlocks.findIndex((b) => b.questionNumbers.includes(current));
      if (idx >= 0) return idx;
    }
    return 0;
  }, [sectionBlocks, current]);

  const activeBlock = sectionBlocks[activeBlockIdx] || null;

  // Đóng ngăn Ví dụ mẫu khi sang phần mới để câu thi thật luôn chiếm trọn khung nhìn
  useEffect(() => {
    setShowExample(false);
  }, [activeBlock?.phanKey]);

  const goToQuestion = useCallback(
    (no) => {
      const target = scored.find((i) => i.so_cau === no);
      if (target && activeSkill && target.ky_nang !== activeSkill) return;
      const staysInSameGroup = activeBlock?.questionNumbers?.length > 1 && activeBlock.questionNumbers.includes(no);
      setCurrent(no);
      setMobilePaletteOpen(false);
      if (staysInSameGroup) {
        requestAnimationFrame(() => {
          document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
      } else if (canvasRef.current) {
        canvasRef.current.scrollTop = 0;
      }
    },
    [scored, activeSkill, activeBlock]
  );

  function stepBlock(delta) {
    const nextIdx = activeBlockIdx + delta;
    if (nextIdx >= 0 && nextIdx < sectionBlocks.length) {
      goToQuestion(sectionBlocks[nextIdx].questionNumbers[0]);
    }
  }

  const handleAdvanceSection = useCallback(async () => {
    if (advancingSection || submitting || saving > 0) return;
    setAdvancingSection(true);
    setError("");
    try {
      const res = await advanceExamSection(token, luotId);
      setActiveSkill(res.ky_nang_hien_tai);
      setLockedSkills(res.cac_phan_da_khoa || []);
      deadline.current = Date.now() + res.con_lai_giay * 1000;
      setSectionConfirmOpen(false);
      setConfirmOpen(false);
      setCurrent(res.vi_tri_hien_tai);
      if (canvasRef.current) canvasRef.current.scrollTop = 0;
    } catch (err) {
      if (err?.status === 409) {
        goResult();
        return;
      }
      setError(err?.message || "Chưa thể chuyển sang phần thi tiếp theo");
      setSectionConfirmOpen(false);
    } finally {
      setAdvancingSection(false);
    }
  }, [advancingSection, submitting, saving, token, luotId, goResult]);

  const unanswered = useMemo(
    () => scored.filter((i) => !i.tra_loi?.phuong_an_chon_id && !(i.tra_loi?.van_ban || "").trim()).map((i) => i.so_cau),
    [scored]
  );
  const unansweredInActiveSec = useMemo(
    () =>
      activeSecScored
        .filter((i) => !i.tra_loi?.phuong_an_chon_id && !(i.tra_loi?.van_ban || "").trim())
        .map((i) => i.so_cau),
    [activeSecScored]
  );
  const answered = scored.length - unanswered.length;
  const activeSecAnswered = activeSecScored.length - unansweredInActiveSec.length;
  const flaggedInActiveSec = useMemo(
    () => activeSecScored.map((i) => i.so_cau).filter((no) => flags.has(no)),
    [activeSecScored, flags]
  );

  // AT22, AT43: Phím tắt mũi tên Trái/Phải khóa biên trong phần đang mở; 1–6 / A–F chọn đáp án; M gắn cờ ⚑
  useEffect(() => {
    if (
      !data ||
      confirmOpen ||
      sectionConfirmOpen ||
      proctorModalOpen ||
      backBlockedOpen ||
      submitting ||
      advancingSection ||
      !activeSecScored.length
    ) {
      return undefined;
    }
    const onKeyDown = (e) => {
      if (e.ctrlKey || e.altKey || e.metaKey) return;
      const tag = (e.target?.tagName || "").toLowerCase();
      if (["input", "textarea", "select"].includes(tag) || e.target?.isContentEditable) return; // AT22

      const activeItem = activeSecScored.find((i) => i.so_cau === current) || activeSecScored[0];
      if (!activeItem) return;

      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        // AT43: Chỉ điều hướng trong phạm vi phần kỹ năng đang mở
        const idx = activeSecScored.findIndex((i) => i.so_cau === activeItem.so_cau);
        const nextIdx = e.key === "ArrowRight" ? idx + 1 : idx - 1;
        if (nextIdx >= 0 && nextIdx < activeSecScored.length) {
          e.preventDefault();
          goToQuestion(activeSecScored[nextIdx].so_cau);
        }
        return;
      }

      const keyUpper = e.key.toUpperCase();
      if (keyUpper === "M") {
        e.preventDefault();
        toggleFlag(activeItem.so_cau);
        return;
      }

      let optIdx = -1;
      if (/^[1-6]$/.test(keyUpper)) optIdx = Number(keyUpper) - 1;
      else if (/^[A-F]$/.test(keyUpper)) optIdx = keyUpper.charCodeAt(0) - 65;

      if (optIdx >= 0 && ["chon_mot", "dung_sai", "chon_bo_chung"].includes(activeItem.cau_hoi.dang)) {
        const opts =
          activeItem.cau_hoi.dang === "chon_bo_chung"
            ? data.ngu_lieu?.[activeItem.cau_cha_id]?.phuong_an ?? []
            : activeItem.cau_hoi.phuong_an ?? [];
        if (optIdx < opts.length) {
          e.preventDefault();
          onPick(activeItem, opts[optIdx].id);
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    data,
    confirmOpen,
    sectionConfirmOpen,
    proctorModalOpen,
    backBlockedOpen,
    submitting,
    advancingSection,
    activeSecScored,
    current,
    goToQuestion,
    onPick,
    toggleFlag,
  ]);

  if (error && !data) {
    return (
      <ExamShell title="Phòng thi thử">
        <p role="alert" className="lv-alert">
          {error}
        </p>
      </ExamShell>
    );
  }
  if (!data) {
    return (
      <ExamShell title="Phòng thi thử">
        <p className="lv-muted">Đang khởi tạo trạm thi HSK bảo mật…</p>
      </ExamShell>
    );
  }

  const low = remaining !== null && remaining <= 300;
  const sharedAudioUrl = mediaUrl(data.de.tep_audio_chung);
  const maxAudioPlays = data.so_luot_nghe_toi_da || 1;
  const activeNo = current ?? activeBlock?.questionNumbers?.[0];

  const candidateInfo = {
    name: user?.ho_ten || "Thí sinh dự thi",
    code: `SBD ${String(user?.id || 0).padStart(4, "0")}-${luotId}`,
    saveText: saving > 0 ? "Đang lưu…" : "✓ Đã lưu",
  };

  // Thanh tiến trình 3 phần một chiều đặt ngay trung tâm Header chuẩn HSK机考
  const headerCenter = (
    <div className="ibt-ws-steps" aria-label="Tiến trình các phần thi">
      {sections.map((sec, idx) => {
        const secScored = scored.filter((i) => i.ky_nang === sec.ky_nang);
        const secDone = secScored.filter(
          (i) => i.tra_loi?.phuong_an_chon_id || (i.tra_loi?.van_ban || "").trim()
        ).length;
        const isActive = activeSkill === sec.ky_nang;
        const isPastLocked = lockedSkills.includes(sec.ky_nang);
        return (
          <span key={sec.ky_nang} className="ibt-ws-step-wrap">
            {idx > 0 && <span className="ibt-ws-step-sep" aria-hidden="true">▸</span>}
            <span
              className={`ibt-ws-step${isActive ? " is-active" : ""}${isPastLocked ? " is-done" : ""}`}
              title={
                isPastLocked
                  ? "Phần thi đã khóa sau khi nộp phần"
                  : isActive
                    ? "Phần thi đang mở"
                    : "Phần thi chưa mở"
              }
            >
              <b>{sec.title}</b>
              <small>
                {isPastLocked
                  ? `🔒 ${secDone}/${secScored.length}`
                  : isActive
                    ? `${secDone}/${secScored.length}`
                    : "Chưa mở"}
              </small>
            </span>
          </span>
        );
      })}
    </div>
  );

  return (
    <ExamShell
      workstation
      title="Kỳ thi năng lực Hán ngữ"
      candidate={candidateInfo}
      center={headerCenter}
      fontScale={fontScale}
      onFontScaleChange={handleFontChange}
      isFullscreen={isFullscreen}
      onToggleFullscreen={toggleFullscreen}
      right={
        <>
          <span
            className={`ibt-ws-proctor-pill${focusStrikes > 0 ? " is-warn" : ""}`}
            title="Bộ đếm giám sát rời màn hình phòng thi (tối đa 3 lần)"
          >
            Giám sát: {Math.min(focusStrikes, MAX_FOCUS_STRIKES)}/{MAX_FOCUS_STRIKES}
          </span>
          <span
            className={`ibt-ws-timer${low ? " is-low" : ""}`}
            role="timer"
            aria-live={low ? "polite" : "off"}
            aria-label="Thời gian còn lại"
          >
            <small>Còn lại</small>
            <strong>{formatClock(remaining ?? 0)}</strong>
          </span>

          {nextSectionMeta ? (
            <button
              type="button"
              className="ibt-ws-submitbtn"
              onClick={() => setSectionConfirmOpen(true)}
              disabled={advancingSection || submitting}
            >
              Nộp phần {activeSectionMeta?.label} →
            </button>
          ) : (
            <button
              type="button"
              className="ibt-ws-submitbtn ibt-ws-submitbtn--final"
              onClick={() => setConfirmOpen(true)}
              disabled={submitting}
            >
              Nộp bài (交卷)
            </button>
          )}
        </>
      }
    >
      <div className="ibt-ws-grid">
        {/* ==================== CỘT TRÁI CỐ ĐỊNH: BẢNG SỐ CÂU (`题号导航`) ==================== */}
        <aside className={`ibt-ws-palette${mobilePaletteOpen ? " is-open" : ""}`} aria-label="Bảng điều hướng câu hỏi">
          <div className="ibt-ws-palette__head">
            <div>
              <strong>Bảng câu hỏi</strong>
              <span>
                Đã trả lời <b>{answered}</b>/{scored.length}
              </span>
            </div>
            <button
              type="button"
              className="ibt-ws-palette__close"
              onClick={() => setMobilePaletteOpen(false)}
              aria-label="Đóng bảng câu hỏi"
            >
              ✕
            </button>
          </div>

          <div className="ibt-ws-palette__scroll">
            <QuestionNav
              items={items}
              sections={sections}
              mode="do"
              flags={flags}
              current={activeNo}
              onSelect={goToQuestion}
              activeSkill={activeSkill}
              lockedSkills={lockedSkills}
            />
          </div>

          <div className="ibt-ws-palette__foot">
            <div className="ibt-legend" aria-hidden="true">
              <span>
                <i className="lg-ans" /> Đã làm
              </span>
              <span>
                <i /> Chưa làm
              </span>
              <span>
                <i className="lg-cur" /> Đang mở
              </span>
              <span>
                <i className="lg-flg" /> Đánh dấu ⚑
              </span>
            </div>

            {flaggedInActiveSec.length > 0 && (
              <p className="ibt-ws-flag-summary">⚑ Đánh dấu: {flaggedInActiveSec.join(", ")}</p>
            )}

            <p className="ibt-shortcut-hint">
              Phím tắt: <code>←</code> <code>→</code> chuyển câu · <code>1–6</code> / <code>A–F</code> chọn ·{" "}
              <code>M</code> gắn cờ
            </p>
          </div>
        </aside>

        {/* ==================== KHUNG CHÍNH BÊN PHẢI: TRẠM LÀM ĐỀ (`主答题区`) ==================== */}
        <main className="ibt-ws-stage">
          {/* Nhắc bật lại Toàn màn hình nếu thí sinh bấm Esc thoát khỏi chế độ Fullscreen */}
          {!isFullscreen && (
            <div className="ibt-ws-fsbanner">
              <span>
                ⛶ Chế độ <b>Toàn màn hình phòng thi</b> đang tắt — vui lòng giữ toàn màn hình trong suốt giờ làm bài.
              </span>
              <button type="button" onClick={toggleFullscreen}>
                Bật Toàn màn hình
              </button>
            </div>
          )}

          {/* 1. Thanh phát băng Nghe tích hợp sát mép trên (tự động phát 1.0x, chống tua) */}
          {activeSkill === "nghe" && sharedAudioUrl && (
            <div className="ibt-ws-audiobar">
              <ProctoredAudioPlayer
                src={sharedAudioUrl}
                storageKey={`xianglingo-audio-${luotId}-sec-nghe`}
                variant="section"
                maxPlays={1}
                autoPlay
                onAllPlaysEnded={() => setListeningTapeEnded(true)}
              />
            </div>
          )}

          {/* Thông báo kết thúc băng Nghe chuẩn HSK机考: nhắc rà nhanh và chuyển sang phần Đọc */}
          {activeSkill === "nghe" && listeningTapeEnded && nextSectionMeta && (
            <div className="ibt-ws-lowbanner" role="status">
              <span>
                🔔 <b>Băng Nghe đã phát xong:</b>{" "}
                {unansweredInActiveSec.length > 0
                  ? `Bạn còn ${unansweredInActiveSec.length} câu Nghe chưa chọn đáp án — hãy hoàn tất ngay rồi nộp phần Nghe.`
                  : `Bạn đã trả lời đủ ${activeSecScored.length}/${activeSecScored.length} câu Nghe — hãy bấm "Nộp phần Nghe →" để sang phần ${nextSectionMeta.label}.`}
              </span>
              <button type="button" onClick={() => setSectionConfirmOpen(true)}>
                Nộp phần Nghe →
              </button>
            </div>
          )}

          {/* Cảnh báo 5 phút cuối chuẩn máy thi HSK */}
          {low && !lowWarnDismissed && (
            <div className="ibt-ws-lowbanner" role="status">
              <span>
                ⚠ <b>Sắp hết giờ làm bài:</b> Thời gian còn dưới 5 phút — hệ thống sẽ tự động thu bài ngay khi chạm{" "}
                <code>00:00</code>.
              </span>
              <button type="button" onClick={() => setLowWarnDismissed(true)}>
                Đã hiểu
              </button>
            </div>
          )}

          {error && (
            <div role="alert" className="ibt-ws-errbanner">
              <span>{error}</span>
              <button type="button" onClick={() => setError("")}>
                Đóng
              </button>
            </div>
          )}

          {/* 2. Thanh tiêu đề Phần thi & Câu đang mở + Nút mở Câu ví dụ mẫu (`例如`) */}
          {activeBlock && (
            <div className="ibt-ws-qhead">
              <div className="ibt-ws-qhead__left">
                <button
                  type="button"
                  className="ibt-ws-mobile-navbtn"
                  onClick={() => setMobilePaletteOpen(true)}
                >
                  ☰ Bảng câu ({answered}/{scored.length})
                </button>
                <span className="ibt-part-pill">
                  {activeBlock.sectionTitle} · {activeBlock.partTitle}
                </span>
                {activeBlock.partFrom && (
                  <span className="ibt-stage-head__range">
                    (第 {activeBlock.partFrom}
                    {activeBlock.partTo !== activeBlock.partFrom ? `–${activeBlock.partTo}` : ""} 题)
                  </span>
                )}
                <span className="ibt-ws-qbadge">
                  {activeBlock.questionNumbers.length > 1
                    ? `Câu ${activeBlock.questionNumbers[0]}–${activeBlock.questionNumbers[activeBlock.questionNumbers.length - 1]}`
                    : `Câu ${activeBlock.questionNumbers[0]}`}
                </span>
              </div>

              <div className="ibt-ws-qhead__right">
                {activeBlock.examples.length > 0 && (
                  <button
                    type="button"
                    className={`ibt-example-toggle${showExample ? " is-open" : ""}`}
                    onClick={() => setShowExample((v) => !v)}
                  >
                    {showExample ? "Ẩn câu mẫu (例如) ▴" : "📖 Xem câu mẫu (例如) ▾"}
                  </button>
                )}
                <span className="ibt-ws-secstat">
                  Phần {activeBlock.sectionLabel}: <b>{activeSecAnswered}</b>/{activeSecScored.length}
                </span>
              </div>
            </div>
          )}

          {/* 3. Vùng nội dung câu hỏi chính diện (chỉ cuộn bên trong vùng này nếu bài đọc dài) */}
          <div className="ibt-ws-canvas" ref={canvasRef}>
            {activeBlock && showExample && activeBlock.examples.length > 0 && (
              <div className="ibt-example-box">
                <div className="ibt-example-box__head">
                  <span className="ibt-example-box__tag">Câu ví dụ mẫu đầu phần (例如 · Không tính điểm)</span>
                  <button type="button" className="ibt-example-box__close" onClick={() => setShowExample(false)}>
                    Đóng ✕
                  </button>
                </div>
                {activeBlock.examples.map((exBlk, idx) =>
                  exBlk.group ? (
                    <GroupBlock
                      key={`ex-g-${idx}`}
                      mode="do"
                      block={exBlk}
                      passage={data.ngu_lieu[exBlk.group]}
                      onPick={() => {}}
                      disabled
                    />
                  ) : (
                    <SingleRow
                      key={`ex-s-${idx}`}
                      mode="do"
                      item={exBlk.items[0]}
                      onPick={() => {}}
                      onText={() => {}}
                      disabled
                    />
                  )
                )}
              </div>
            )}

            {activeBlock && (
              <div className="ibt-ws-question-card">
                {activeBlock.block.group ? (
                  <GroupBlock
                    key={`g-${activeBlock.block.group}`}
                    mode="do"
                    block={activeBlock.block}
                    passage={data.ngu_lieu[activeBlock.block.group]}
                    activeQuestionNo={activeNo}
                    onFocusQuestion={setCurrent}
                    onPick={(item, oid) => {
                      setCurrent(item.so_cau);
                      onPick(item, oid);
                    }}
                    disabled={submitting || advancingSection}
                    luotId={luotId}
                    showItemAudio={activeBlock.ky_nang === "nghe" && !sharedAudioUrl}
                    maxAudioPlays={maxAudioPlays}
                  />
                ) : (
                  <SingleRow
                    key={activeBlock.block.items[0].cau_hoi.id}
                    mode="do"
                    item={activeBlock.block.items[0]}
                    onPick={(item, oid) => {
                      setCurrent(item.so_cau);
                      onPick(item, oid);
                    }}
                    onText={(item, val) => {
                      setCurrent(item.so_cau);
                      onText(item, val);
                    }}
                    disabled={submitting || advancingSection}
                    luotId={luotId}
                    showItemAudio={activeBlock.ky_nang === "nghe" && !sharedAudioUrl}
                    maxAudioPlays={maxAudioPlays}
                  />
                )}
              </div>
            )}
          </div>

          {/* 4. Thanh điều hướng ghim cố định cạnh dưới (`上一题 · 标记 · 下一题`) */}
          {activeBlock && (
            <footer className="ibt-ws-foot">
              <div className="ibt-ws-foot__flags">
                {activeBlock.questionNumbers.map((no) => (
                  <button
                    key={no}
                    type="button"
                    className={`ibt-ws-flagbtn${flags.has(no) ? " is-on" : ""}`}
                    onClick={() => toggleFlag(no)}
                    aria-pressed={flags.has(no)}
                  >
                    <span aria-hidden="true">⚑</span>{" "}
                    {activeBlock.questionNumbers.length > 1
                      ? `${flags.has(no) ? "Đã đánh dấu" : "Đánh dấu"} câu ${no}`
                      : flags.has(no)
                        ? `Đã đánh dấu xem lại (Câu ${no})`
                        : "Đánh dấu xem lại (Phím M)"}
                  </button>
                ))}
              </div>

              <div className="ibt-ws-foot__nav">
                <button
                  type="button"
                  className="xbtn xbtn--ghost xbtn--sm"
                  disabled={activeBlockIdx <= 0}
                  onClick={() => stepBlock(-1)}
                >
                  ← Câu trước (上一题)
                </button>
                {activeBlockIdx < sectionBlocks.length - 1 ? (
                  <button type="button" className="xbtn xbtn--sm" onClick={() => stepBlock(1)}>
                    Câu tiếp theo (下一题) →
                  </button>
                ) : nextSectionMeta ? (
                  <button
                    type="button"
                    className="xbtn xbtn--sm"
                    onClick={() => setSectionConfirmOpen(true)}
                    disabled={advancingSection || submitting}
                  >
                    Nộp phần {activeBlock.sectionLabel} · Sang phần {nextSectionMeta.label} →
                  </button>
                ) : (
                  <button
                    type="button"
                    className="xbtn xbtn--sm"
                    onClick={() => setConfirmOpen(true)}
                    disabled={submitting}
                  >
                    Kiểm tra & Nộp bài (交卷)
                  </button>
                )}
              </div>
            </footer>
          )}
        </main>
      </div>

      {/* HỘP XÁC NHẬN CHỐT KHÓA MỘT CHIỀU & CHUYỂN PHẦN KỸ NĂNG (`Nghe → Đọc → Viết`) */}
      {sectionConfirmOpen && nextSectionMeta && (
        <div className="xt-dialog" role="dialog" aria-modal="true" aria-labelledby="xt-sec-confirm-title">
          <div className="xt-dialog__box">
            {unansweredInActiveSec.length > 0 ? (
              <>
                <h2 id="xt-sec-confirm-title">Chưa thể nộp phần {activeSectionMeta?.label}</h2>
                <p>
                  Phần <b>{activeSectionMeta?.label}</b> còn <b>{unansweredInActiveSec.length} câu chưa trả lời</b>. Theo
                  quy chế HSK máy tính, sau khi chuyển sang phần <b>{nextSectionMeta.label}</b> bạn sẽ{" "}
                  <b>không thể quay lại</b> phần này — hãy hoàn thành đủ các câu bên dưới trước:
                </p>
                <div className="xt-flagjump">
                  {unansweredInActiveSec.map((no) => (
                    <button
                      key={no}
                      type="button"
                      className="xt-nav__btn"
                      onClick={() => {
                        setSectionConfirmOpen(false);
                        goToQuestion(no);
                      }}
                    >
                      {no}
                    </button>
                  ))}
                </div>
                <div className="lv-actions">
                  <button
                    type="button"
                    className="xbtn"
                    onClick={() => {
                      setSectionConfirmOpen(false);
                      goToQuestion(unansweredInActiveSec[0]);
                    }}
                  >
                    Đi tới câu {unansweredInActiveSec[0]}
                  </button>
                  <button type="button" className="xbtn xbtn--ghost" onClick={() => setSectionConfirmOpen(false)}>
                    Đóng
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 id="xt-sec-confirm-title">
                  Nộp khóa phần {activeSectionMeta?.label} để sang phần {nextSectionMeta.label}?
                </h2>
                <p>
                  Bạn đã trả lời đủ{" "}
                  <b>
                    {activeSecScored.length}/{activeSecScored.length}
                  </b>{" "}
                  câu của phần <b>{activeSectionMeta?.label}</b>. Lưu ý theo quy chế HSK trên máy tính (严禁跨区): ngay
                  khi mở phần <b>{nextSectionMeta.label}</b>, phần <b>{activeSectionMeta?.label}</b> sẽ bị{" "}
                  <b>khóa vĩnh viễn</b> và không thể quay lại xem hay sửa đáp án.
                </p>
                {flaggedInActiveSec.length > 0 && (
                  <div className="xt-flagjump">
                    <span>Câu đang đánh dấu ⚑ trong phần này:</span>
                    {flaggedInActiveSec.map((no) => (
                      <button
                        key={no}
                        type="button"
                        className="xt-nav__btn is-flag"
                        onClick={() => {
                          setSectionConfirmOpen(false);
                          goToQuestion(no);
                        }}
                      >
                        {no}
                      </button>
                    ))}
                  </div>
                )}
                <div className="lv-actions">
                  <button
                    type="button"
                    className="xbtn"
                    onClick={handleAdvanceSection}
                    disabled={advancingSection || saving > 0}
                  >
                    {advancingSection ? "Đang khóa & mở phần tiếp…" : `Xác nhận sang phần ${nextSectionMeta.label}`}
                  </button>
                  <button
                    type="button"
                    className="xbtn xbtn--ghost"
                    onClick={() => setSectionConfirmOpen(false)}
                    disabled={advancingSection}
                  >
                    Quay lại kiểm tra phần {activeSectionMeta?.label}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* HỘP XÁC NHẬN NỘP BÀI THI CUỐI CÙNG (AT19) */}
      {confirmOpen && (
        <div className="xt-dialog" role="dialog" aria-modal="true" aria-labelledby="xt-confirm-title">
          <div className="xt-dialog__box">
            {unanswered.length > 0 ? (
              <>
                <h2 id="xt-confirm-title">Chưa thể nộp bài sớm</h2>
                <p>
                  Bạn còn <b>{unansweredInActiveSec.length} câu tính điểm chưa trả lời</b> trong phần{" "}
                  <b>{activeSectionMeta?.label}</b>. Hãy chọn số câu bên dưới để hoàn thành trước khi nộp bài:
                </p>
                <div className="xt-flagjump">
                  {unansweredInActiveSec.map((no) => (
                    <button
                      key={no}
                      type="button"
                      className="xt-nav__btn"
                      onClick={() => {
                        setConfirmOpen(false);
                        goToQuestion(no);
                      }}
                    >
                      {no}
                    </button>
                  ))}
                </div>
                <div className="lv-actions">
                  {unansweredInActiveSec[0] && (
                    <button
                      type="button"
                      className="xbtn"
                      onClick={() => {
                        setConfirmOpen(false);
                        goToQuestion(unansweredInActiveSec[0]);
                      }}
                    >
                      Đi tới câu {unansweredInActiveSec[0]}
                    </button>
                  )}
                  <button type="button" className="xbtn xbtn--ghost" onClick={() => setConfirmOpen(false)}>
                    Đóng
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 id="xt-confirm-title">Xác nhận nộp bài thi (交卷)?</h2>
                <p>
                  Bạn đã hoàn thành đầy đủ{" "}
                  <b>
                    {answered}/{scored.length}
                  </b>{" "}
                  câu tính điểm của kỳ thi.
                </p>
                {flaggedInActiveSec.length > 0 && (
                  <div className="xt-flagjump">
                    <span>Câu bạn đang đánh dấu xem lại ở phần cuối:</span>
                    {flaggedInActiveSec.map((no) => (
                      <button
                        key={no}
                        type="button"
                        className="xt-nav__btn is-flag"
                        onClick={() => {
                          setConfirmOpen(false);
                          goToQuestion(no);
                        }}
                      >
                        {no}
                      </button>
                    ))}
                  </div>
                )}
                <div className="lv-actions">
                  <button
                    type="button"
                    className="xbtn"
                    onClick={() => submit(false)}
                    disabled={submitting || saving > 0}
                  >
                    {submitting ? "Đang chấm & nộp bài…" : "Xác nhận nộp bài"}
                  </button>
                  <button
                    type="button"
                    className="xbtn xbtn--ghost"
                    onClick={() => setConfirmOpen(false)}
                    disabled={submitting}
                  >
                    Quay lại rà bài
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* HỘP CẢNH BÁO GIÁM THỊ KHI CHUYỂN TAB / THU NHỎ MÀN HÌNH (`切屏警告 1/3 · 2/3`) */}
      {proctorModalOpen && (
        <div className="xt-dialog" role="dialog" aria-modal="true" aria-labelledby="xt-proctor-title">
          <div className="xt-dialog__box">
            <h2 id="xt-proctor-title" style={{ color: "var(--bad)" }}>
              ⚠ Cảnh báo rời màn hình thi ({Math.min(focusStrikes, MAX_FOCUS_STRIKES)}/{MAX_FOCUS_STRIKES})
            </h2>
            <p>
              Hệ thống giám sát vừa ghi nhận thao tác <b>chuyển sang tab khác hoặc thu nhỏ cửa sổ phòng thi</b> (切屏).
            </p>
            <p>
              Theo quy chế thi HSK trực tuyến, thí sinh tuyệt đối không mở trang tra cứu bên ngoài trong giờ làm bài.
              Nếu vi phạm đủ <b>{MAX_FOCUS_STRIKES} lần</b> (còn{" "}
              <b>{Math.max(0, MAX_FOCUS_STRIKES - focusStrikes)} lần</b>), hệ thống sẽ{" "}
              <b>tự động lập biên bản và thu bài ngay lập tức</b>.
            </p>
            <div className="lv-actions">
              <button
                type="button"
                className="xbtn"
                onClick={() => {
                  setProctorModalOpen(false);
                  if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen?.().catch(() => {});
                  }
                }}
              >
                Tôi đã hiểu & Tiếp tục làm bài
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HỘP CHẶN NÚT BACK (←) CỦA TRÌNH DUYỆT TRONG GIỜ LÀM BÀI */}
      {backBlockedOpen && (
        <div className="xt-dialog" role="dialog" aria-modal="true" aria-labelledby="xt-back-title">
          <div className="xt-dialog__box">
            <h2 id="xt-back-title">Đang trong giờ làm bài thi bảo mật</h2>
            <p>
              Nút <b>Quay lại (Back)</b> của trình duyệt đã được khóa để bảo vệ phiên thi và không làm gián đoạn băng
              Nghe. Đồng hồ máy chủ vẫn đang đếm ngược — vui lòng hoàn thành bài thi và bấm nộp theo quy chế.
            </p>
            <div className="lv-actions">
              <button type="button" className="xbtn" onClick={() => setBackBlockedOpen(false)}>
                Quay lại làm bài
              </button>
            </div>
          </div>
        </div>
      )}
    </ExamShell>
  );
}
