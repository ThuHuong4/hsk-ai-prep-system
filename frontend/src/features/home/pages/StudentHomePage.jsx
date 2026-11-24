/**
 * Trang chủ Cá nhân hóa của Học viên (`/hoc-vien`) — thiết kế chuẩn AI Diagnostic Studio:
 * - Hiện rõ trình độ HSK hiện tại trên thanh lộ trình 4 cấp (1..L đã mở, > L đang khóa).
 * - Hiển thị bảng 4 kỹ năng HSK (Từ vựng, Nghe, Đọc, Viết) trực quan.
 * - Hiển thị Khối Nhận định tổng hợp của Xiang AI + Thẻ Điểm yếu phân biệt rõ "Lỗi lặp lại (AT39)"
 *   và "Tín hiệu cần bù ban đầu", gắn trực tiếp nút mở Bài ôn khắc phục ngay.
 * - Có nút tra cứu gọn "Biên bản đánh giá gốc" bên trong thẻ Hồ sơ AI (phục vụ kiểm chứng mà không làm rối giao diện).
 */
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { startNotebookReview } from "../../notebook/api/notebookApi.js";
import DailyMissions from "../../notebook/components/DailyMissions.jsx";
import { getPlacementGate } from "../../placement/api/placementApi.js";
import { getPersonalDashboard, startLesson } from "../../practice/api/practiceApi.js";
import { skillSlug } from "../../practice/utils/skills.js";
import "../styles/studentDashboard.css";

const firstName = (name) => (name || "").trim().split(/\s+/).pop() || "bạn";

const WEAK_TYPE_LABEL = {
  loi_kien_thuc: "Lỗ hổng lặp lại khi luyện tập",
  can_goi_y: "Cần củng cố độ tự chủ",
  khao_sat_dau_vao: "Tín hiệu cần bù ban đầu",
};

export default function StudentHomePage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const { data: gate } = useRequest((signal) => getPlacementGate(token, signal), [token]);
  const { data: dash, error, loading } = useRequest((signal) => getPersonalDashboard(token, signal), [token]);
  const [busyLessonId, setBusyLessonId] = useState(null);
  const [busyReview, setBusyReview] = useState(false);
  const [actionErr, setActionErr] = useState("");

  if (gate?.tu_dong_chuyen_huong) {
    return <Navigate to={gate.tu_dong_chuyen_huong} replace />;
  }

  async function openLessonByItem(item) {
    if (!item || busyLessonId != null) return;
    if (item.luot_dang_lam) {
      navigate(`/on-luyen/bai/${item.luot_dang_lam}`);
      return;
    }
    setBusyLessonId(item.ma_goc_id);
    setActionErr("");
    try {
      const res = await startLesson(token, item.ma_goc_id);
      navigate(`/on-luyen/bai/${res.luot_id}`);
    } catch (err) {
      setActionErr(err?.message || "Chưa mở được bài học này");
      setBusyLessonId(null);
    }
  }

  async function handleQuickNotebookReview() {
    if (busyReview) return;
    setBusyReview(true);
    setActionErr("");
    try {
      const res = await startNotebookReview(token);
      navigate(`/so-tay/on/${res.luot_id}`);
    } catch (err) {
      setActionErr(err?.message || "Chưa mở được lượt ôn Sổ tay");
      setBusyReview(false);
    }
  }

  const trinhDo = dash?.trinh_do_hien_tai;
  const allLevels = dash?.muc_tieu?.danh_sach_cap ?? [];
  const todayLesson = dash?.bai_hom_nay;
  const profile = dash?.ho_so_nang_luc;
  const aiInsights = profile?.nhan_dinh_ai ?? [];
  const skillCards = profile?.ky_nang_4_chieu ?? [];
  const weakSpots = profile?.diem_can_cai_thien ?? [];
  const strengths = profile?.diem_manh ?? [];
  const placement = dash?.dau_vao_gan_nhat;
  const notebook = dash?.so_tay;
  const openExam = dash?.luot_thi_dang_lam;
  const name = firstName(user?.ho_ten);
  const currentOrder = trinhDo?.thu_tu || 1;

  return (
    <section className="xc sh">
      {openExam && (
        <div className="sd-alert-exam">
          <div>
            <b>Đang có bài Thi thử chưa nộp</b>
            <p className="xc-muted">
              Còn khoảng {Math.max(1, Math.ceil(openExam.con_lai_giay / 60))} phút làm bài trong phòng thi.
            </p>
          </div>
          <Link className="xc-btn xc-btn--coral xc-btn--sm" to={`/thi-thu/lam-bai/${openExam.luot_id}`}>
            Quay lại phòng thi <Icon name="arrow" />
          </Link>
        </div>
      )}

      <div className="sh-dash">
        <div className="sh-col">
          {/* KHỐI 1: BẢNG TRÌNH ĐỘ HSK HIỆN TẠI, THANH MỞ KHÓA 4 CẤP & BÀI TRỌNG TÂM HÔM NAY */}
          <div className="sd-hero">
            <div className="sd-hero__head">
              <div className="sd-hero__intro">
                <span className="sd-hero__eyebrow">
                  <Icon name="spark" size={15} />
                  {trinhDo ? `Hồ sơ năng lực AI · Trình độ ${trinhDo.ten}` : "Lộ trình cá nhân hóa"}
                </span>
                <h1>
                  {trinhDo
                    ? `Chào ${name}, bạn đang ở trình độ ${trinhDo.ten}`
                    : `Chào ${name}, cùng bắt đầu hôm nay nhé!`}
                </h1>
                <p className="sd-hero__sub">
                  {trinhDo?.cac_cap_dang_khoa?.length > 0
                    ? `Hệ thống đã mở khóa ${trinhDo.cac_cap_da_mo.join(", ")} ở cả 4 kỹ năng và tạm khóa ${trinhDo.cac_cap_dang_khoa.join(", ")} để bạn lấp chắc các lỗ hổng nền tảng trước khi nâng cấp.`
                    : "Toàn bộ lộ trình HSK 1 – HSK 4 đã mở khóa cho bạn."}
                </p>
              </div>
              <img className="sd-hero__masc" src={xiangFace} alt="" />
            </div>

            {allLevels.length > 0 && (
              <div className="sd-level-track" role="list" aria-label="Trạng thái mở khóa các cấp HSK">
                {allLevels.map((lv) => {
                  const isCurrent = lv.thu_tu === currentOrder;
                  const isUnlocked = lv.thu_tu <= currentOrder;
                  const cls = isCurrent ? " is-current" : isUnlocked ? " is-unlocked" : " is-locked";
                  return (
                    <div key={lv.id} role="listitem" className={`sd-lv-step${cls}`}>
                      <b>{lv.ten}</b>
                      <small>
                        {isCurrent ? "★ Trình độ hiện tại" : isUnlocked ? "✓ Đã mở khóa" : "🔒 Đang khóa"}
                      </small>
                    </div>
                  );
                })}
              </div>
            )}

            {/* KHUNG QUY TẮC & TIẾN ĐỘ THĂNG LÊN CẤP HSK TIẾP THEO (GHI RÕ CHỮ CHO NGƯỜI HỌC) */}
            {trinhDo?.cap_tiep_theo && (
              <div className="sd-levelup-box">
                <div className="sd-levelup-box__body">
                  <span className="sd-levelup-box__kicker">
                    Làm thế nào để nâng từ Trình độ {trinhDo.ten} lên Trình độ {trinhDo.cap_tiep_theo}?
                  </span>
                  <div className="sd-levelup-box__ways">
                    <span>
                      <b>Cách 1 — Thi thử đạt chuẩn {trinhDo.ten}:</b> Làm bài trong mục Thi thử và đạt từ{" "}
                      <b>
                        {trinhDo.diem_dat_thi} trên {trinhDo.diem_toi_da_thi} điểm trở lên
                      </b>
                      {trinhDo.diem_thi_cao_nhat != null
                        ? ` (điểm thi cao nhất hiện tại của bạn: ${Math.round(trinhDo.diem_thi_cao_nhat)}/${trinhDo.diem_toi_da_thi} điểm).`
                        : " (bạn chưa làm bài thi thử nào ở cấp này)."}
                    </span>
                    <span>
                      <b>Cách 2 — Hoàn thành vượt cấp trên Lộ trình ôn:</b> Thi vượt cấp mở khóa đủ cả{" "}
                      <b>{trinhDo.tong_ky_nang} kỹ năng (Nghe, Đọc, Từ vựng, Viết)</b> lên {trinhDo.cap_tiep_theo} (hiện
                      tại bạn đã mở{" "}
                      <b>
                        {trinhDo.so_ky_nang_vuot_cap ?? 0} trên {trinhDo.tong_ky_nang ?? 4} kỹ năng
                      </b>
                      ).
                    </span>
                  </div>
                </div>
                <Link className="sd-levelup-box__cta" to="/hoc-vien/thi-thu">
                  Vào phòng Thi thử
                </Link>
              </div>
            )}

            {loading && <p className="sd-hero__sub">Đang tổng hợp chẩn đoán AI và lộ trình ưu tiên của bạn…</p>}
            {error && <p role="alert">{error}</p>}
            {actionErr && <p role="alert">{actionErr}</p>}

            {todayLesson ? (
              <div className="sd-focus-card">
                <div className="sd-focus-card__info">
                  <span className="sd-focus-card__badge">{todayLesson.nhan_uu_tien}</span>
                  <span className="sd-focus-card__title">
                    {todayLesson.ten_cap} · {todayLesson.ten_ky_nang} — {todayLesson.ten_bai}
                    {todayLesson.ten_thua ? ` (${todayLesson.ten_thua})` : ""}
                  </span>
                  <span className="sd-focus-card__desc">{todayLesson.ly_do}</span>
                </div>
                <div className="sd-focus-card__acts">
                  <button
                    type="button"
                    className="xc-btn xc-btn--coral xc-btn--sm"
                    disabled={busyLessonId != null}
                    onClick={() => openLessonByItem(todayLesson)}
                  >
                    {busyLessonId === todayLesson.ma_goc_id
                      ? "Đang mở bài…"
                      : todayLesson.trang_thai === "dang_lam"
                        ? "Làm tiếp bài dở"
                        : "Học ngay bài ưu tiên"}{" "}
                    <Icon name="arrow" />
                  </button>
                </div>
              </div>
            ) : !loading ? (
              <div>
                <Link className="xc-btn xc-btn--coral xc-btn--sm" to="/hoc-vien/on-luyen">
                  Mở bản đồ ôn luyện <Icon name="arrow" />
                </Link>
              </div>
            ) : null}
          </div>

          {/* KHỐI 2: CHỈ SỐ 4 KỸ NĂNG HSK TRỰC QUAN */}
          {skillCards.length > 0 && (
            <div className="sd-skill-grid" aria-label="Tổng quan 4 kỹ năng HSK">
              {skillCards.map((sk) => {
                const isWeak = sk.trang_thai_nhan === "Cần ưu tiên bù";
                return (
                  <Link
                    key={sk.ky_nang}
                    to={`/hoc-vien/on-luyen/${skillSlug(sk.ky_nang)}`}
                    className={`sd-skill-card${isWeak ? " is-weak" : ""}`}
                  >
                    <div className="sd-skill-card__top">
                      <strong>{sk.ten_ky_nang}</strong>
                      <span className="sd-skill-card__pct">
                        {sk.so_cau_da_lam > 0 ? `${sk.ty_le_vung}%` : "—"}
                      </span>
                    </div>
                    <div className="sd-skill-card__bar" aria-hidden="true">
                      <i style={{ width: `${sk.so_cau_da_lam > 0 ? Math.max(8, sk.ty_le_vung) : 0}%` }} />
                    </div>
                    <small>{sk.trang_thai_nhan}</small>
                  </Link>
                );
              })}
            </div>
          )}

          {/* KHỐI 3: TỔNG HỢP PHÂN TÍCH AI & CHỦ ĐIỂM CẦN BÙ */}
          {dash && (
            <div className="sd-section-card">
              <div className="sd-section-head">
                <div className="sd-section-head__title">
                  <Icon name="spark" />
                  <h2>Phân tích năng lực AI & Bài ôn ưu tiên</h2>
                </div>
                {placement && (
                  <Link
                    className="sh-link"
                    to={`/danh-gia-dau-vao/ket-qua/${placement.luot_id}`}
                    style={{ fontSize: "13px" }}
                  >
                    Biên bản đánh giá gốc →
                  </Link>
                )}
              </div>

              {aiInsights.length > 0 && (
                <ul className="plm-insights">
                  {aiInsights.slice(0, 3).map((ins) => (
                    <li key={ins.thu_tu} className={`plm-insight plm-insight--${ins.loai}`}>
                      <b>
                        {ins.ten_ky_nang}
                        {ins.ten_nhom ? ` · ${ins.ten_nhom}` : ""}
                      </b>
                      <p style={{ marginTop: "3px", fontSize: "14px", color: "var(--ink-2)" }}>{ins.noi_dung}</p>
                    </li>
                  ))}
                </ul>
              )}

              {weakSpots.length > 0 ? (
                <ul className="sd-weak-list">
                  {weakSpots.map((w, idx) => {
                    const remedy = w.bai_on_khac_phuc;
                    return (
                      <li key={`${w.ky_nang}-${w.nhom_kien_thuc_id || idx}`} className="sd-weak-card">
                        <div className="sd-weak-card__head">
                          <div className="sd-weak-card__topic">
                            <span className={`xc-tag xc-tag--${w.ky_nang}`}>{w.ten_ky_nang}</span>
                            <strong>{w.ten_nhom}</strong>
                          </div>
                          <span className="sd-weak-card__source">
                            {WEAK_TYPE_LABEL[w.loai] || "Cần củng cố"} · {w.mo_ta}
                          </span>
                        </div>

                        {w.phan_tich_ai && <p className="sd-weak-card__ai">{w.phan_tich_ai}</p>}

                        {remedy && (
                          <div className="sd-remedy">
                            <div className="sd-remedy__meta">
                              <small>Bài ôn khắc phục được ưu tiên</small>
                              <b>
                                {remedy.ten_cap} · {remedy.ten_bai}
                                {remedy.ten_thua ? ` (${remedy.ten_thua})` : ""}
                              </b>
                            </div>
                            <button
                              type="button"
                              className="xc-btn xc-btn--sm"
                              disabled={busyLessonId != null}
                              onClick={() => openLessonByItem(remedy)}
                            >
                              {busyLessonId === remedy.ma_goc_id ? "Đang mở…" : "Ôn khắc phục ngay"}{" "}
                              <Icon name="arrow" />
                            </button>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="xc-muted">
                  Hiện chưa phát hiện lỗ hổng kiến thức nổi bật nào. Bạn hãy tiếp tục chinh phục các bài mới trong lộ trình {trinhDo?.ten || "HSK 1"}!
                </p>
              )}

              {strengths.length > 0 && (
                <div>
                  <small className="xc-muted" style={{ display: "block", fontWeight: 700, marginBottom: "8px" }}>
                    Chủ điểm bạn đã nắm vững:
                  </small>
                  <div className="sd-strength-chips">
                    {strengths.map((s, idx) => (
                      <Link
                        key={idx}
                        to={`/hoc-vien/on-luyen/${skillSlug(s.ky_nang)}`}
                        className="sd-strength-chip"
                      >
                        ✓ {s.ten_ky_nang} · {s.ten_nhom} ({s.ty_le}%)
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* CỘT PHẢI: NHIỆM VỤ HẰNG NGÀY, SỔ TAY LẶP LẠI NGẮT QUÃNG & PHÒNG THI THỬ NGẪU NHIÊN */}
        <div className="sh-col">
          <DailyMissions />

          <div className="sh-panel">
            <div className="sh-panel__head sh-panel__head--bad">
              <Icon name="book" />
              <h2>Sổ tay đến hạn hôm nay</h2>
            </div>
            {notebook && notebook.den_han > 0 ? (
              <>
                <p>
                  Bạn có <b>{notebook.den_han} câu sai đến hạn ôn lặp lại</b> hôm nay
                  {notebook.da_cung_co > 0 ? ` (đã củng cố vững ${notebook.da_cung_co} câu)` : ""}. Ôn Sổ tay miễn phí năng lượng.
                </p>
                <button
                  type="button"
                  className="xc-btn xc-btn--sm"
                  disabled={busyReview}
                  onClick={handleQuickNotebookReview}
                >
                  {busyReview ? "Đang mở…" : `Ôn ngay ${Math.min(10, notebook.den_han)} câu đến hạn`}
                </button>
              </>
            ) : (
              <>
                <p>
                  {notebook?.da_cung_co > 0
                    ? `Bạn không còn câu nào quá hạn hôm nay và đã củng cố vững ${notebook.da_cung_co} câu.`
                    : "Chưa có câu sai nào đến hạn ôn hôm nay. Câu làm sai khi luyện bài sẽ tự động lưu vào đây để nhắc ôn đúng chu kỳ."}
                </p>
                <Link className="sh-link" to="/hoc-vien/so-tay-cau-sai">
                  Mở Sổ tay câu sai →
                </Link>
              </>
            )}
          </div>

          <div className="sh-panel">
            <div className="sh-panel__head">
              <Icon name="timer" />
              <h2>Phòng thi thử ngẫu nhiên</h2>
            </div>
            <p>
              Đề thi được hệ thống rút ngẫu nhiên bảo mật theo trình độ {trinhDo?.ten || "HSK"} (không biết trước đề), bấm giờ chuẩn và chấm giải thích chi tiết sau khi nộp.
            </p>
            <Link className="xc-btn xc-btn--exam xc-btn--sm" to="/hoc-vien/thi-thu">
              Vào phòng thi thử <Icon name="arrow" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
