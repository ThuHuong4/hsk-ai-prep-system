/**
 * Phiếu Báo Điểm Kỳ Thi Thử HSK (`ExamResultPage.jsx` — chuẩn `HSK成绩报告单` + Đối chiếu AI):
 * - Công bố chính thức cấp độ đề vừa thi (sau khi giữ kín trong lúc thi), tổng điểm, ngưỡng đạt, thời gian làm bài thực tế và điểm thành phần trên thang `/100`.
 * - Đảm bảo quy chế đồng nhất: muốn thi đề mới luôn quay về Phòng chờ (`/hoc-vien/thi-thu`) để qua cổng Kiểm tra âm thanh & Cam kết quy chế.
 * - Tích hợp Bộ lọc thông minh `Tất cả · Chưa đạt / Câu sai · Câu đạt` và Bảng đối chiếu chia theo từng kỹ năng (`Nghe · Đọc · Viết`).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { mediaUrl } from "../../../shared/utils/format.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { getResult } from "../api/mockTestApi.js";
import ExamPaper from "../components/ExamPaper.jsx";
import ExamShell from "../components/ExamShell.jsx";
import QuestionNav from "../components/QuestionNav.jsx";
import RoadmapCard from "../components/RoadmapCard.jsx";
import { buildPaper } from "../utils/paper.js";

const SKILL = {
  nghe: { vi: "Nghe hiểu", zh: "听力" },
  doc: { vi: "Đọc hiểu", zh: "阅读" },
  viet: { vi: "Viết", zh: "书写" },
  tu_vung: { vi: "Từ vựng", zh: "词汇" },
};

function formatDurationUsed(startIso, endIso) {
  if (!startIso || !endIso) return "—";
  const diffSec = Math.max(1, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000));
  const m = Math.floor(diffSec / 60);
  const s = diffSec % 60;
  if (m <= 0) return `${s} giây`;
  return s > 0 ? `${m} phút ${String(s).padStart(2, "0")} giây` : `${m} phút`;
}

export default function ExamResultPage() {
  const { luotId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const backPath = location.state?.from || "/hoc-vien/thi-thu";
  const backLabel =
    location.state?.from === "/hoc-vien/lich-su-thi" ? "Quay về Lịch sử thi" : "Quay về Phòng thi thử";
  const { token, user } = useAuth();
  const { data, error, loading } = useRequest((signal) => getResult(token, luotId, signal), [token, luotId]);
  const [reviewFilter, setReviewFilter] = useState("all"); // "all" | "wrong" | "correct"

  // Đồng bộ làm mới ngay huy hiệu Trình độ HSK trên thanh đầu trang khi vừa thi Đạt thăng cấp
  useEffect(() => {
    if (data) {
      window.dispatchEvent(new Event("xianglingo:stats"));
    }
  }, [data]);

  // Rời Phiếu báo điểm bằng pop/replace để không để lại `/thi-thu/ket-qua/:id` kẹt trong lịch sử nút Back của Phòng chờ
  const handleLeaveResult = useCallback(() => {
    if (location.state?.from === "/hoc-vien/lich-su-thi" || location.state?.fromLobby) {
      navigate(-1);
    } else {
      navigate(backPath, { replace: true });
    }
  }, [location.state, navigate, backPath]);

  const allSections = useMemo(() => (data ? buildPaper(data.cau_hoi) : []), [data]);

  const filteredItems = useMemo(() => {
    if (!data) return [];
    if (reviewFilter === "all") return data.cau_hoi;
    return data.cau_hoi.filter((it) => {
      if (it.la_cau_vi_du) return false;
      if (reviewFilter === "wrong") return it.ket_qua?.dung !== true;
      if (reviewFilter === "correct") return it.ket_qua?.dung === true;
      return true;
    });
  }, [data, reviewFilter]);

  const filteredSections = useMemo(() => buildPaper(filteredItems), [filteredItems]);

  const jumpToQuestion = useCallback(
    (no) => {
      if (!data) return;
      const target = data.cau_hoi.find((i) => !i.la_cau_vi_du && i.so_cau === no);
      const isOk = target?.ket_qua?.dung === true;
      const hiddenByFilter =
        (reviewFilter === "wrong" && isOk) || (reviewFilter === "correct" && !isOk);
      if (hiddenByFilter) {
        setReviewFilter("all");
        setTimeout(() => {
          document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 80);
      } else {
        document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    [data, reviewFilter]
  );

  if (loading) {
    return (
      <ExamShell title="Phiếu báo điểm HSK">
        <p className="lv-muted">Đang tổng hợp Phiếu báo điểm…</p>
      </ExamShell>
    );
  }
  if (error) {
    return (
      <ExamShell title="Phiếu báo điểm HSK">
        <p role="alert" className="lv-alert">
          {error}
        </p>
      </ExamShell>
    );
  }

  const d = data.diem;
  const scoredItems = data.cau_hoi.filter((i) => !i.la_cau_vi_du);
  const correctCount = scoredItems.filter((i) => i.ket_qua?.dung === true).length;
  const wrongCount = scoredItems.length - correctCount;
  const accuracyPct = scoredItems.length > 0 ? Math.round((correctCount / scoredItems.length) * 100) : 0;
  const maxPerSkill = d.ky_nang.length > 0 ? Math.round(d.diem_toi_da / d.ky_nang.length) : 100;
  const durationText = formatDurationUsed(data.bat_dau_luc, data.nop_luc);

  function scrollToAnchor(id) {
    if (!id) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <ExamShell
      title={`Phiếu báo điểm · ${data.de.ten}`}
      onBack={handleLeaveResult}
      backLabel={backLabel}
      right={
        <>
          <nav className="ibt-res-jumpnav" aria-label="Chuyển nhanh tới mục">
            <button type="button" onClick={() => scrollToAnchor("")}>
              <Icon name="chart" size={15} /> Phiếu điểm
            </button>
            <button type="button" onClick={() => scrollToAnchor("ibt-sec-roadmap")}>
              <Icon name="spark" size={15} /> Chẩn đoán AI
            </button>
            <button type="button" onClick={() => scrollToAnchor("ibt-sec-review")}>
              <Icon name="doc" size={15} /> Lời giải
            </button>
          </nav>
          <Link to="/hoc-vien" replace className="xg-icon-btn ibt-icon-tip" data-tip="Trang chủ" aria-label="Về Trang chủ">
            <Icon name="home" size={18} />
          </Link>
        </>
      }
    >
      <div className="xt-layout">
        <main className="xt-main">
          {/* ==================== 1. PHIẾU BÁO ĐIỂM CHUẨN HSK (`HSK成绩报告单`) ==================== */}
          <section className={`ibt-cert${d.dat ? " is-pass" : ""}`} aria-label="Phiếu báo điểm HSK">
            <header className="ibt-cert__banner">
              <div>
                <span className="ibt-cert__seal">汉语水平考试成绩报告单 · HSK SCORE REPORT</span>
                <h1>{data.de.ten}</h1>
              </div>
              <span
                className={`ibt-cert__badge ${
                  d.so_cau_cho_cham ? "is-pending" : d.dat ? "is-pass" : "is-fail"
                }`}
              >
                {d.so_cau_cho_cham
                  ? `Đang chờ chấm (${d.so_cau_cho_cham})`
                  : d.dat
                    ? "✓ ĐẠT CHUẨN HSK"
                    : "CHƯA ĐẠT CHUẨN"}
              </span>
            </header>

            {/* Dải thông tin Thí sinh & Ca thi */}
            <dl className="ibt-cert__meta">
              <div>
                <dt>Họ tên thí sinh</dt>
                <dd>{user?.ho_ten || "Học viên"}</dd>
              </div>
              <div>
                <dt>Cấp độ & Điểm chuẩn</dt>
                <dd>
                  {data.de.ten_cap_do} · Đạt từ {d.diem_dat}/{d.diem_toi_da}
                </dd>
              </div>
              <div>
                <dt>Thời gian hoàn thành</dt>
                <dd>{durationText}</dd>
              </div>
              <div>
                <dt>Trạng thái thu bài</dt>
                <dd>{data.ly_do_nop === "het_gio" ? "Tự động thu khi hết giờ" : "Hoàn tất nộp bài"}</dd>
              </div>
            </dl>

            {/* Dải thông báo Thăng cấp Trình độ HSK chính thức hoặc Mục tiêu điểm còn thiếu */}
            {data.thang_cap?.cap_tiep_theo && !d.so_cau_cho_cham && (
              <div className={`ibt-cert__promo ${data.thang_cap.dat_chuan ? "is-up" : "is-goal"}`}>
                {data.thang_cap.dat_chuan ? (
                  <span>
                    🎉 <b>Chúc mừng thăng cấp trình độ!</b> Bạn đã đạt chuẩn <b>{data.thang_cap.cap_de_thi}</b> (từ{" "}
                    {d.diem_dat}/{d.diem_toi_da} điểm) — Tài khoản đã chính thức nâng lên{" "}
                    <b>Trình độ {data.thang_cap.cap_tiep_theo}</b> và mở khóa toàn bộ lộ trình ôn luyện{" "}
                    {data.thang_cap.cap_tiep_theo}!
                  </span>
                ) : (
                  <span>
                    🎯 <b>Điều kiện thăng lên Trình độ {data.thang_cap.cap_tiep_theo}:</b> Cần đạt từ{" "}
                    <b>
                      {d.diem_dat}/{d.diem_toi_da} điểm
                    </b>{" "}
                    (bài thi này còn thiếu <b>{Math.max(1, Math.ceil(data.thang_cap.diem_con_thieu))} điểm</b>). Hãy ôn
                    kỹ các nhóm câu yếu bên dưới rồi thử sức lại!
                  </span>
                )}
              </div>
            )}

            {/* Lưới Điểm Tổng & Điểm Thành Phần */}
            <div className="ibt-cert__body">
              <div className="ibt-cert__total">
                <span className="ibt-cert__total-cap">TỔNG ĐIỂM {data.de.ten_cap_do}</span>
                <strong className="ibt-cert__total-num">{d.tong_diem.toFixed(0)}</strong>
                <span className="ibt-cert__total-max">trên thang {d.diem_toi_da} điểm</span>
                <span className="ibt-cert__acc-pill">
                  Đúng {correctCount}/{scoredItems.length} câu ({accuracyPct}%)
                </span>
              </div>

              <div className="ibt-cert__skills">
                <div className="ibt-cert__skills-head">
                  <span>Điểm thành phần theo kỹ năng</span>
                  <span>Thang điểm chuẩn</span>
                </div>

                <div className="ibt-cert__skill-list">
                  {d.ky_nang.map((s) => {
                    const meta = SKILL[s.ky_nang] || { vi: s.ky_nang, zh: "" };
                    const pct = Math.min(100, Math.round((s.diem / maxPerSkill) * 100));
                    return (
                      <div key={s.ky_nang} className="ibt-cert__skill-row">
                        <div className="ibt-cert__skill-top">
                          <span className="ibt-cert__skill-name">
                            <b>{meta.vi}</b> {meta.zh && <small>({meta.zh})</small>}
                          </span>
                          <span className="ibt-cert__skill-score">
                            <strong>{s.diem.toFixed(0)}</strong>
                            <small> / {maxPerSkill}</small>
                          </span>
                        </div>
                        <div className="ibt-cert__bar" aria-hidden="true">
                          <i
                            className={pct >= 60 ? "is-good" : pct >= 40 ? "is-mid" : "is-low"}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="ibt-cert__skill-sub">
                          Đạt {s.dung}/{s.so_cau} câu tính điểm ({pct}%)
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="ibt-cert__actions">
                  <button type="button" className="xbtn" onClick={handleLeaveResult}>
                    Về phòng chờ thi đề mới →
                  </button>
                  <Link className="xbtn xbtn--ghost" replace to="/hoc-vien/on-luyen">
                    Vào lộ trình ôn tập
                  </Link>
                  <Link className="xbtn xbtn--ghost" replace to="/hoc-vien/lich-su-thi">
                    Lịch sử thi thử
                  </Link>
                </div>
              </div>
            </div>
          </section>

          {/* ==================== 2. CHẨN ĐOÁN AI & KẾ HOẠCH CẢI THIỆN ==================== */}
          <div id="ibt-sec-roadmap" style={{ scrollMarginTop: "80px" }}>
            <RoadmapCard luotId={luotId} onJumpQuestion={jumpToQuestion} />
          </div>

          {/* ==================== 3. ĐỐI CHIẾU ĐỀ THI, GIẢI THÍCH & HỎI XIANG ==================== */}
          <div id="ibt-sec-review" className="ibt-review-bar" style={{ scrollMarginTop: "80px" }}>
            <div>
              <h2>Đối chiếu bài làm & Giải thích chi tiết</h2>
              <p>Mở lời giải từng câu hoặc trao đổi trực tiếp với Trợ giảng AI Xiang ngay dưới câu hỏi.</p>
            </div>

            <div className="ibt-review-tabs" role="tablist" aria-label="Bộ lọc câu hỏi xem lại">
              <button
                type="button"
                role="tab"
                aria-selected={reviewFilter === "all"}
                className={`ibt-review-tab${reviewFilter === "all" ? " is-active" : ""}`}
                onClick={() => setReviewFilter("all")}
              >
                Tất cả ({scoredItems.length})
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={reviewFilter === "wrong"}
                className={`ibt-review-tab ibt-review-tab--bad${reviewFilter === "wrong" ? " is-active" : ""}`}
                onClick={() => setReviewFilter("wrong")}
              >
                Chưa đạt / Câu sai ({wrongCount})
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={reviewFilter === "correct"}
                className={`ibt-review-tab${reviewFilter === "correct" ? " is-active" : ""}`}
                onClick={() => setReviewFilter("correct")}
              >
                Câu đạt ({correctCount})
              </button>
            </div>
          </div>

          {filteredSections.length > 0 ? (
            <ExamPaper
              sections={filteredSections}
              passages={data.ngu_lieu}
              mode="review"
              luotId={Number(luotId)}
              onPick={() => {}}
              onText={() => {}}
              disabled
              audioUrl={mediaUrl(data.de.tep_audio_chung)}
            />
          ) : (
            <div className="xt-cover">
              <p>
                {reviewFilter === "wrong"
                  ? "Tuyệt vời! Bạn không có câu sai nào trong bài thi này."
                  : "Không có câu hỏi nào thuộc bộ lọc đang chọn."}
              </p>
            </div>
          )}
        </main>

        {/* CỘT PHẢI: PHIẾU ĐỐI CHIẾU CHIA THEO TỪNG KỸ NĂNG */}
        <aside className="xt-side">
          <div className="xt-side__card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <p className="xt-side__stat">Phiếu đối chiếu</p>
              <span style={{ fontSize: "12.5px", fontWeight: 700, color: "var(--ink-3)" }}>
                {correctCount}/{scoredItems.length} đạt
              </span>
            </div>

            <QuestionNav
              items={data.cau_hoi}
              sections={allSections}
              mode="review"
              onSelect={jumpToQuestion}
            />

            <div className="ibt-legend" aria-hidden="true">
              <span>
                <span className="xt-dot is-ok" style={{ margin: 0 }} /> Câu đạt ({correctCount})
              </span>
              <span>
                <span className="xt-dot is-bad" style={{ margin: 0 }} /> Chưa đạt ({wrongCount})
              </span>
            </div>
          </div>
        </aside>
      </div>
    </ExamShell>
  );
}
