/**
 * Báo cáo Chẩn đoán Năng lực HSK 8 câu (phong cách WriteMate.io Assessment Report).
 * - Hiển thị Trình độ xếp lớp (HSK 1 – HSK 4), thanh 4 cấp mở khóa và chỉ số 4 kỹ năng.
 * - Hiển thị bộ thẻ Chẩn đoán AI đa tiêu chí cho từng câu 1..8 (có bộ lọc Tất cả / Điểm yếu / Đã vững).
 * - Kèm nhận định tổng hợp theo kỹ năng, bài ôn khởi đầu đề xuất và thiết lập mục tiêu cá nhân.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import "../../../layouts/staffShell.css";
import AiDiagnosticPanel from "../../../shared/components/AiDiagnosticPanel.jsx";
import HanziText from "../../../shared/components/HanziText.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { LATIN, SKILL } from "../../../shared/components/LessonParts.jsx";
import "../../../shared/styles/aiDiagnostic.css";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import "../../home/styles/studentDashboard.css";
import { startLesson } from "../../practice/api/practiceApi.js";
import { analyzePlacement, getPlacementResult, savePlacementGoal } from "../api/placementApi.js";
import "../styles/placement.css";

const INSIGHT_LABEL = {
  diem_manh: "Điểm mạnh",
  diem_yeu: "Cần ưu tiên củng cố",
  nhan_xet: "Tổng kết năng lực",
};

export default function PlacementResultPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();

  const [data, setData] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [focusSlot, setFocusSlot] = useState(null);
  const [filterMode, setFilterMode] = useState("all"); // all | weak | strong
  const [goalCapId, setGoalCapId] = useState("");
  const [goalMinutes, setGoalMinutes] = useState("");
  const [goalSaved, setGoalSaved] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);

  const runAnalyze = useCallback(async () => {
    setAnalyzing(true);
    setError("");
    try {
      const res = await analyzePlacement(token, luotId);
      setData(res);
      setGoalCapId(res.muc_tieu_hien_tai?.cap_muc_tieu_id || "");
      setGoalMinutes(res.muc_tieu_hien_tai?.phut_moi_ngay || "");
      window.dispatchEvent(new Event("xianglingo:stats"));
    } catch (err) {
      setError(err?.message || "Quá trình phân tích tạm thời gián đoạn. Bạn bấm Thử lại nhé.");
    } finally {
      setAnalyzing(false);
    }
  }, [token, luotId]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    getPlacementResult(token, luotId, controller.signal)
      .then((res) => {
        if (!active) return;
        setData(res);
        setGoalCapId(res.muc_tieu_hien_tai?.cap_muc_tieu_id || "");
        setGoalMinutes(res.muc_tieu_hien_tai?.phut_moi_ngay || "");
        if (res.trang_thai_phan_tich === "chua") {
          runAnalyze();
        }
      })
      .catch((err) => {
        if (active && err?.name !== "AbortError") {
          setError(err?.message || "Không tải được báo cáo đánh giá đầu vào");
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [token, luotId, runAnalyze]);

  function jumpToEvidence(slotNo) {
    setFilterMode("all");
    setFocusSlot(slotNo);
    setTimeout(() => {
      document.getElementById(`plm-ev-${slotNo}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  async function handleStartLesson(maGocId) {
    setActionBusy(true);
    setError("");
    try {
      const res = await startLesson(token, maGocId);
      navigate(`/on-luyen/bai/${res.luot_id}`);
    } catch (err) {
      setError(err?.message || "Không mở được bài học này");
      setActionBusy(false);
    }
  }

  async function handleSaveGoal(e) {
    e.preventDefault();
    setActionBusy(true);
    setGoalSaved(false);
    try {
      await savePlacementGoal(token, {
        cap_do_id: goalCapId ? Number(goalCapId) : null,
        phut_moi_ngay: goalMinutes ? Number(goalMinutes) : null,
      });
      setGoalSaved(true);
    } catch (err) {
      setError(err?.message || "Chưa lưu được mục tiêu học tập");
    } finally {
      setActionBusy(false);
    }
  }

  if (!data || analyzing || data.trang_thai_phan_tich === "dang") {
    return (
      <div className="xg xc" data-theme={theme}>
        <div className="plm-res">
          <AiDiagnosticPanel mode="analyzing" staticCard />
          {error && (
            <div className="plm-card" style={{ marginTop: "16px", textAlign: "center" }}>
              <p role="alert">{error}</p>
              <button type="button" className="xc-btn" onClick={runAnalyze}>
                Thử phân tích lại
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (data.trang_thai_phan_tich === "loi") {
    return (
      <div className="xg xc" data-theme={theme}>
        <div className="plm-res">
          <div className="plm-card" style={{ textAlign: "center", padding: "2rem" }}>
            <h1>Phân tích tạm thời chưa hoàn tất</h1>
            <p className="xc-muted">
              Các câu trả lời của bạn đều được lưu an toàn. Hãy bấm nút bên dưới để chạy lại bước phân tích.
            </p>
            {error && <p role="alert">{error}</p>}
            <div style={{ marginTop: "1rem" }}>
              <button type="button" className="xc-btn" onClick={runAnalyze} disabled={analyzing}>
                Thử phân tích lại ngay
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const capDeXuat = data.phan_2_cap_de_xuat?.cap_do;
  const allLevels = data.muc_tieu_hien_tai?.danh_sach_cap || [];
  const capOrder = capDeXuat?.thu_tu || 1;
  const skillStats = data.ky_nang_thong_ke || [];
  const filteredItems = data.chi_tiet_8_cau.filter((c) => {
    if (filterMode === "weak") return c.trang_thai_thao_tac === "bo_qua" || c.dung === false;
    if (filterMode === "strong") return c.dung === true;
    return true;
  });

  return (
    <div className="xg xc" data-theme={theme}>
      <div className="plm-res" style={{ maxWidth: "1020px" }}>
        {/* TỔNG KẾT TRÌNH ĐỘ ĐẠT ĐƯỢC & THANH MỞ KHÓA CẤP ĐỘ */}
        <section className="sd-hero" style={{ marginBottom: "20px" }}>
          <div className="sd-hero__head">
            <div className="sd-hero__intro">
              <span className="sd-hero__eyebrow">
                <Icon name="spark" size={15} />
                Báo cáo đánh giá năng lực AI · Đúng {data.tong_quan_diem.so_cau_dung}/{data.tong_quan_diem.so_cau_hop_le} câu
              </span>
              <h1>Trình độ xác định: {capDeXuat ? capDeXuat.ten : "HSK 1"}</h1>
              <p className="sd-hero__sub">{data.phan_2_cap_de_xuat?.tuyen_bo}</p>
            </div>
            <img className="sd-hero__masc" src={xiangFace} alt="" />
          </div>

          {allLevels.length > 0 && (
            <div className="sd-level-track">
              {allLevels.map((lv) => {
                const isCurrent = lv.thu_tu === capOrder;
                const isUnlocked = lv.thu_tu <= capOrder;
                const cls = isCurrent ? " is-current" : isUnlocked ? " is-unlocked" : " is-locked";
                return (
                  <div key={lv.id} className={`sd-lv-step${cls}`}>
                    <b>{lv.ten}</b>
                    <small>
                      {isCurrent ? "★ Trình độ xếp lớp" : isUnlocked ? "✓ Đã mở khóa" : "🔒 Đang khóa"}
                    </small>
                  </div>
                );
              })}
            </div>
          )}

          {data.ghi_chu_gioi_han && <p className="sd-hero__sub">Lưu ý: {data.ghi_chu_gioi_han}</p>}

          <div className="sd-focus-card__acts">
            <Link className="xc-btn xc-btn--coral xc-btn--sm" to="/hoc-vien">
              Vào Trang chủ cá nhân hóa <Icon name="arrow" />
            </Link>
            <Link className="xc-btn xc-btn--plain xc-btn--sm" to="/hoc-vien/on-luyen">
              Xem bản đồ 4 kỹ năng
            </Link>
          </div>
        </section>

        {error && <p role="alert">{error}</p>}

        {/* BẢNG 4 KỸ NĂNG TRONG BÀI KHẢO SÁT */}
        {skillStats.length > 0 && (
          <div className="sd-skill-grid" style={{ marginBottom: "20px" }}>
            {skillStats.map((sk) => (
              <div
                key={sk.ky_nang}
                className={`sd-skill-card${sk.phan_tram < 50 ? " is-weak" : ""}`}
              >
                <div className="sd-skill-card__top">
                  <strong>{sk.ten_ky_nang}</strong>
                  <span className="sd-skill-card__pct">
                    {sk.dung}/{sk.tong} câu
                  </span>
                </div>
                <div className="sd-skill-card__bar">
                  <i style={{ width: `${sk.tong > 0 ? Math.max(8, sk.phan_tram) : 0}%` }} />
                </div>
                <small>
                  {sk.phan_tram === 100
                    ? "Nắm vững ở bài khảo sát"
                    : sk.bo_qua > 0
                      ? `Có ${sk.bo_qua} câu chưa biết`
                      : "Cần ưu tiên củng cố"}
                </small>
              </div>
            ))}
          </div>
        )}

        {/* PHẦN 1: NHẬN ĐỊNH TỔNG HỢP CỦA AI THEO KỸ NĂNG */}
        <section className="sd-section-card" style={{ marginBottom: "20px" }}>
          <div className="sd-section-head">
            <div className="sd-section-head__title">
              <Icon name="chart" />
              <h2>1. Nhận định tổng hợp theo kỹ năng</h2>
            </div>
          </div>
          <ul className="plm-insights">
            {data.phan_1_nhan_dinh.map((ins) => (
              <li key={ins.thu_tu} className={`plm-insight plm-insight--${ins.loai}`}>
                <div>
                  <b>
                    {INSIGHT_LABEL[ins.loai] || "Nhận xét"}
                    {ins.ky_nang ? ` · ${SKILL[ins.ky_nang] || ins.ky_nang}` : ""}
                    {ins.ten_nhom ? ` (${ins.ten_nhom})` : ""}
                  </b>
                  <p style={{ marginTop: "4px" }}>{ins.noi_dung}</p>
                </div>
                {ins.bang_chung?.length > 0 && (
                  <div className="plm-chips">
                    {ins.bang_chung.map((cNo) => (
                      <button key={cNo} type="button" className="plm-chip" onClick={() => jumpToEvidence(cNo)}>
                        Đối chiếu câu {cNo}
                      </button>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>

        {/* PHẦN 2: CHẨN ĐOÁN CHI TIẾT TỪNG CÂU (1..8) KIỂU WRITEMATE */}
        <section className="sd-section-card" style={{ marginBottom: "20px" }}>
          <div className="sd-section-head">
            <div className="sd-section-head__title">
              <Icon name="spark" />
              <h2>2. Chẩn đoán chuyên sâu từng câu (Câu 1 – Câu 8)</h2>
            </div>
            <div className="sd-filter-tabs" role="tablist" aria-label="Lọc câu đánh giá">
              {[
                ["all", `Tất cả (${data.chi_tiet_8_cau.length})`],
                ["weak", "Điểm yếu & Chưa biết"],
                ["strong", "Đã nắm vững"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={filterMode === key}
                  className={`sd-filter-tab${filterMode === key ? " is-active" : ""}`}
                  onClick={() => setFilterMode(key)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gap: "16px" }}>
            {filteredItems.map((c) => (
              <article
                key={c.thu_tu}
                id={`plm-ev-${c.thu_tu}`}
                className={`sd-report-qcard${focusSlot === c.thu_tu ? " is-focus" : ""}`}
              >
                {c.noi_dung && (
                  <div className="sd-report-qcard__stem">
                    {LATIN.test(c.noi_dung) ? (
                      <span>{c.noi_dung}</span>
                    ) : (
                      <HanziText text={c.noi_dung} pinyin={c.pinyin} />
                    )}
                  </div>
                )}
                <AiDiagnosticPanel mode="result" staticCard result={c} />
              </article>
            ))}
          </div>
        </section>

        {/* PHẦN 3: BÀI HỌC BẮT ĐẦU ĐỀ XUẤT & MỤC TIÊU CÁ NHÂN */}
        <section className="sd-section-card">
          <div className="sd-section-head">
            <div className="sd-section-head__title">
              <Icon name="route" />
              <h2>3. Bài ôn khởi đầu đề xuất ở {capDeXuat?.ten || "HSK 1"}</h2>
            </div>
          </div>

          {data.phan_3_bai_nen_hoc.length > 0 ? (
            <ul className="plm-rec-list">
              {data.phan_3_bai_nen_hoc.map((rec) => (
                <li key={rec.thu_tu} className="plm-rec-item">
                  <div>
                    <b>
                      {rec.ten_cap} · {SKILL[rec.ky_nang] || rec.ky_nang} · {rec.ten_thua} — {rec.ten_bai}
                    </b>
                    <p className="xc-muted" style={{ marginTop: "4px", fontSize: "14px" }}>
                      {rec.ly_do}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="xc-btn xc-btn--sm"
                    disabled={actionBusy}
                    onClick={() => handleStartLesson(rec.ma_goc_id)}
                  >
                    Học ngay <Icon name="arrow" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="xc-muted">Lộ trình {capDeXuat?.ten || "HSK 1"} ở cả 4 kỹ năng đã mở sẵn cho bạn.</p>
          )}

          <form onSubmit={handleSaveGoal} style={{ paddingTop: "14px", borderTop: "1px solid var(--line)" }}>
            <b>Mục tiêu HSK bạn hướng tới (tùy chọn)</b>
            <div className="plm-goal-row">
              <select
                aria-label="Bạn muốn chinh phục HSK mấy?"
                value={goalCapId}
                onChange={(e) => {
                  setGoalCapId(e.target.value);
                  setGoalSaved(false);
                }}
                style={{ padding: "9px 12px", borderRadius: "10px", border: "1px solid var(--line-2)", background: "var(--surface)", color: "var(--ink)" }}
              >
                <option value="">-- Chọn cấp HSK mục tiêu --</option>
                {allLevels.map((lv) => (
                  <option key={lv.id} value={lv.id}>
                    {lv.ten}
                  </option>
                ))}
              </select>
              <select
                aria-label="Thời lượng học mỗi ngày"
                value={goalMinutes}
                onChange={(e) => {
                  setGoalMinutes(e.target.value);
                  setGoalSaved(false);
                }}
                style={{ padding: "9px 12px", borderRadius: "10px", border: "1px solid var(--line-2)", background: "var(--surface)", color: "var(--ink)" }}
              >
                <option value="">-- Thời lượng mỗi ngày --</option>
                <option value="10">10 phút / ngày</option>
                <option value="15">15 phút / ngày</option>
                <option value="30">30 phút / ngày</option>
                <option value="60">60 phút / ngày</option>
              </select>
              <button type="submit" className="xc-btn xc-btn--plain xc-btn--sm" disabled={actionBusy}>
                Lưu mục tiêu
              </button>
              {goalSaved && <span style={{ alignSelf: "center", fontWeight: 700, color: "var(--good)" }}>✓ Đã lưu mục tiêu!</span>}
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
