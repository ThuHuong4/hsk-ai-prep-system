import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

import Icon from "../../../shared/components/Icon.jsx";
import { RANKS, rankOf } from "../../../shared/utils/rank.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import DailyMissions from "../../notebook/components/DailyMissions.jsx";
import LevelUpDialog from "../../profile/components/LevelUpDialog.jsx";
import "../styles/levelTest.css";
import "../styles/practice.css";
import "../styles/statsRules.css";

// Bậc đã thấy lần trước (mỗi trình duyệt): lên bậc mới thì hiện hộp chúc mừng một lần
function seenRank(uid, value) {
  const key = `xianglingo-bac-${uid}`;
  try {
    if (value === undefined) {
      const v = Number(localStorage.getItem(key));
      return Number.isFinite(v) && v > 0 ? v : null;
    }
    localStorage.setItem(key, String(value));
  } catch {
    // trình duyệt chặn lưu trữ: bỏ qua hiệu ứng lên bậc
  }
  return null;
}

// Hộp giải thích: gắn vào khung .xg (thanh trên có backdrop-filter làm position: fixed bị cắt),
// tiêu đề + nút X luôn ở trên, nút Đóng luôn ở dưới, chỉ phần nội dung cuộn. Esc hoặc bấm nền để đóng.
function RuleDialog({ title, labelId, onClose, actions, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const host = document.querySelector(".xg") || document.body;
  return createPortal(
    <div
      className="sr-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelId}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="sr-box">
        <header className="sr-head">
          <h2 id={labelId}>{title}</h2>
          <button type="button" className="sr-x" onClick={onClose} aria-label="Đóng">
            ×
          </button>
        </header>
        <div className="sr-body">{children}</div>
        <footer className="sr-foot">{actions}</footer>
      </div>
    </div>,
    host,
  );
}

/**
 * Thanh chỉ số cố định đầu trang Học viên:
 * - Bấm vào `Trình độ HSK` -> mở bảng giải thích rõ chữ Quy tắc nâng trình độ HSK.
 * - Bấm vào `Điểm KN / Danh hiệu`, `Năng lượng` hoặc `Chuỗi ngày` -> mở bảng giải thích rõ chữ Cách tính Điểm kinh nghiệm (KN), Bậc danh hiệu, Năng lượng & Chuỗi ngày.
 */
export default function StudentStats({ stats, compact = false }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [levelUp, setLevelUp] = useState(null);
  const [modalKind, setModalKind] = useState(null); // "hsk" | "kn" | null
  const rank = stats?.kn != null ? rankOf(stats.kn) : null;
  const uid = user?.ma_nguoi_dung;
  const trinhDo = stats?.trinh_do;
  const levelName = trinhDo?.ten;

  useEffect(() => {
    if (!rank || !uid || compact) return;
    const before = seenRank(uid);
    if (before !== null && rank.bac > before) setLevelUp(rank);
    if (before === null || rank.bac > before) seenRank(uid, rank.bac);
  }, [rank?.bac, uid, compact]); // eslint-disable-line react-hooks/exhaustive-deps

  if (stats?.nang_luong == null) return null;

  const pillBtnStyle = {
    background: "var(--surface)",
    border: "1px solid var(--line-2)",
    borderRadius: 999,
    padding: "0 12px",
    minHeight: 38,
    color: "inherit",
    cursor: "pointer",
  };

  return (
    <span className={`sp-stats${compact ? " sp-stats--compact" : ""}`}>
      {levelName && (
        <button
          type="button"
          className="sp-stat sp-stat--level"
          onClick={() => setModalKind("hsk")}
          title={trinhDo?.cap_tiep_theo ? `Trình độ hiện tại · Bấm để xem cách lên ${trinhDo.cap_tiep_theo}` : "Xem thông tin trình độ HSK"}
          style={{
            ...pillBtnStyle,
            background: "var(--teal-soft)",
            border: "1px solid color-mix(in srgb, var(--teal) 38%, transparent)",
            color: "var(--teal-ink)",
          }}
        >
          <Icon name="layers" size={16} />
          <b>{levelName}</b>
        </button>
      )}

      {!compact && (
        <button
          type="button"
          className="sp-stat sp-stat--fire"
          onClick={() => setModalKind("kn")}
          style={pillBtnStyle}
          title="Chuỗi ngày học liên tiếp · Bấm để xem quy tắc"
        >
          <Icon name="flame" size={17} />
          <b>{stats.chuoi_ngay ?? 0}</b>
          <small>ngày</small>
        </button>
      )}

      <button
        type="button"
        className="sp-stat sp-stat--energy"
        onClick={() => setModalKind("energy")}
        style={pillBtnStyle}
        title="Bấm để mở Nhiệm vụ & quy tắc hồi năng lượng"
      >
        <Icon name="sprout" size={17} />
        <b>
          {stats.nang_luong}/{stats.nang_luong_toi_da}
        </b>
        {stats.nang_luong === 0 && <small>· Hồi ngay</small>}
      </button>

      {!compact && (
        <button
          type="button"
          className="sp-stat sp-stat--kn"
          onClick={() => setModalKind("kn")}
          style={pillBtnStyle}
          title="Điểm kinh nghiệm & Danh hiệu · Bấm để xem cách tính"
        >
          <Icon name="bolt" size={17} />
          <b>{stats.kn} KN</b>
          <small>· {rank ? rank.ten : "Sơ học"}</small>
        </button>
      )}

      {levelUp && <LevelUpDialog rank={levelUp} onClose={() => setLevelUp(null)} />}

      {/* 1. HỘP GIẢI THÍCH RÕ CHỮ QUY TẮC THĂNG CẤP TRÌNH ĐỘ HSK */}
      {modalKind === "hsk" && trinhDo && (
        <RuleDialog
          title={`Trình độ hiện tại của bạn: ${levelName}`}
          labelId="hsk-rule-dlg"
          onClose={() => setModalKind(null)}
          actions={<>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setModalKind(null)}>
                Đóng
              </button>
              <button
                type="button"
                className="xc-btn xc-btn--plain xc-btn--sm"
                onClick={() => {
                  setModalKind(null);
                  navigate("/hoc-vien/on-luyen");
                }}
              >
                Vào Lộ trình ôn
              </button>
              {trinhDo.cap_tiep_theo && (
                <button
                  type="button"
                  className="xc-btn xc-btn--sm"
                  onClick={() => {
                    setModalKind(null);
                    navigate("/hoc-vien/thi-thu");
                  }}
                >
                  Vào Thi thử lên cấp
                </button>
              )}
</>}
        >
            {trinhDo.cap_tiep_theo ? (
              <>
                <p style={{ margin: "0 0 10px", fontSize: 14.5, color: "var(--ink-2)", lineHeight: 1.55 }}>
                  Hiện tại bạn được học và ôn lại toàn bộ các bài từ <b>HSK 1 đến {levelName}</b>. Các cấp cao hơn đang
                  tạm khóa để bạn nắm vững kiến thức nền tảng.
                </p>
                <p style={{ margin: "0 0 8px", fontSize: 14.5, fontWeight: 700, color: "var(--ink)" }}>
                  Để chính thức nâng trình độ tài khoản lên {trinhDo.cap_tiep_theo}, bạn chỉ cần đạt 1 trong 2 điều kiện
                  sau:
                </p>
                <ul style={{ marginBottom: 14 }}>
                  <li>
                    <b>Cách 1 — Thi thử đạt chuẩn {levelName}:</b> Vào mục <b>Thi thử</b> làm đề bấm giờ và đạt từ{" "}
                    <b>
                      {trinhDo.diem_dat_thi} trên {trinhDo.diem_toi_da_thi} điểm trở lên
                    </b>
                    {trinhDo.diem_thi_cao_nhat != null
                      ? ` (điểm thi cao nhất của bạn ở ${levelName} hiện là ${Math.round(trinhDo.diem_thi_cao_nhat)}/${trinhDo.diem_toi_da_thi} điểm).`
                      : ` (bạn chưa có lượt thi thử ${levelName} nào).`}
                  </li>
                  <li>
                    <b>Cách 2 — Hoàn thành vượt cấp đủ 4 kỹ năng:</b> Trong mục <b>Lộ trình ôn</b>, vượt qua bài kiểm
                    tra mở khóa lên {trinhDo.cap_tiep_theo} ở đủ cả <b>4 kỹ năng (Nghe, Đọc, Từ vựng, Viết)</b> — hiện
                    tại bạn đã mở{" "}
                    <b>
                      {trinhDo.so_ky_nang_vuot_cap ?? 0}/{trinhDo.tong_ky_nang ?? 4} kỹ năng
                    </b>
                    .
                  </li>
                </ul>
                <p style={{ margin: "0 0 16px", fontSize: 13.8, color: "var(--teal-ink)", fontWeight: 600 }}>
                  Ngay khi hoàn thành 1 trong 2 cách trên, tài khoản sẽ tự động nâng lên Trình độ{" "}
                  {trinhDo.cap_tiep_theo}, mở khóa toàn bộ bài học {trinhDo.cap_tiep_theo} và nâng đề Thi thử lên{" "}
                  {trinhDo.cap_tiep_theo}.
                </p>
              </>
            ) : (
              <p style={{ margin: "0 0 16px", fontSize: 14.5, color: "var(--ink-2)", lineHeight: 1.55 }}>
                Chúc mừng bạn! Bạn đã đạt cấp độ cao nhất trên hệ thống (<b>{levelName}</b>) và mở khóa toàn bộ bài học
                từ HSK 1 đến HSK 4 ở cả 4 kỹ năng.
              </p>
            )}
        </RuleDialog>
      )}

      {/* 1B. HỘP NĂNG LƯỢNG & NHIỆM VỤ HỒI NĂNG LƯỢNG TRỰC TIẾP */}
      {modalKind === "energy" && (
        <RuleDialog
          title={`Năng lượng hiện tại: ${stats.nang_luong}/${stats.nang_luong_toi_da}`}
          labelId="energy-rule-dlg"
          onClose={() => setModalKind(null)}
          actions={
            <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setModalKind(null)}>
              Đóng
            </button>
          }
        >
          {stats.nang_luong === 0 && (
            <div className="sr-now" style={{ marginBottom: "12px", borderColor: "var(--coral, #D95F43)" }}>
              <b>Bạn đã hết năng lượng (0/{stats.nang_luong_toi_da})!</b>
              <p style={{ margin: "4px 0 0", fontSize: "14px" }}>
                Hãy vào <b>Sổ tay câu sai</b> làm đúng từ <b>80%</b> để hồi ngay <b>+1 🌱</b> (không giới hạn số lần trong ngày), hoặc làm <b>Nhiệm vụ ngày</b> bên dưới.
              </p>
            </div>
          )}
          <DailyMissions onNavigate={() => setModalKind(null)} />
          <h3 className="sr-h" style={{ marginTop: "14px" }}>Bình Năng lượng mở rộng theo Trình độ HSK</h3>
          <ul className="sr-list">
            <li>
              <b>Trần năng lượng theo cấp HSK:</b> <b>HSK 1: 5/5</b> · <b>HSK 2: 6/6</b> · <b>HSK 3: 8/8</b> · <b>HSK 4: 10/10</b> (tự mở rộng ngay khi bạn thăng cấp và tự hồi đầy vào đầu mỗi ngày mới).
            </li>
            <li>
              Học bài mới hoặc làm lại bài chưa đạt: mỗi câu trả lời sai hoặc bỏ qua bị trừ <b>−1 năng lượng</b> (câu sai tự động lưu vào <b>Sổ tay câu sai</b>).
            </li>
            <li>
              <b>Hồi năng lượng không bị kẹt:</b> (1) Mỗi nhiệm vụ ngày hoàn thành nhận <b>+1 🌱</b>; (2) Mỗi lượt <b>Ôn Sổ tay đạt ≥ 80% câu đúng</b> tự hồi ngay <b>+1 🌱</b> (nhiều lần trong ngày tới đầy bình {stats.nang_luong_toi_da}/{stats.nang_luong_toi_da}); (3) Vượt <b>Kiểm tra cuối thửa 10/10</b> thưởng nóng <b>+1 🌱</b>.
            </li>
            <li>
              <b>Miễn phí năng lượng:</b> Ôn Sổ tay câu sai, Ôn lại bài đã xong, Kiểm tra Vượt thửa/Bắt đầu cấp và Thi thử đều <b>không tốn năng lượng</b>.
            </li>
          </ul>
        </RuleDialog>
      )}

      {/* 2. CÁCH TÍNH KN, DANH HIỆU, NĂNG LƯỢNG & CHUỖI NGÀY */}
      {modalKind === "kn" && (
        <RuleDialog
          title="Cách tính Kinh nghiệm, Năng lượng & Chuỗi ngày"
          labelId="kn-rule-dlg"
          onClose={() => setModalKind(null)}
          actions={
            <>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setModalKind(null)}>
                Đóng
              </button>
              <button
                type="button"
                className="xc-btn xc-btn--sm"
                onClick={() => {
                  setModalKind(null);
                  navigate("/hoc-vien/ca-nhan");
                }}
              >
                Xem danh hiệu của tôi
              </button>
            </>
          }
        >
          <div className="sr-now">
            <div className="sr-now__top">
              <span>
                <b>{stats.kn} KN</b> · Bậc {rank?.bac}/{RANKS.length}: <b>{rank?.ten}</b> ({rank?.zh})
              </span>
              <small>{rank?.next ? `Còn ${rank.con_thieu} KN lên "${rank.next.ten}"` : "Danh hiệu cao nhất"}</small>
            </div>
            <div className="sr-bar" aria-hidden="true">
              <i style={{ width: `${Math.round((rank?.ti_le ?? 0) * 100)}%` }} />
            </div>
          </div>

          <h3 className="sr-h">1. Cộng KN khi nào?</h3>
          <table className="sr-table">
            <thead>
              <tr>
                <th>Hoạt động</th>
                <th>KN</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Đạt 1 bài ôn (đúng hết các câu)</td>
                <td className="sr-kn">+10</td>
              </tr>
              <tr>
                <td>Đạt Kiểm tra cuối thửa (10/10)</td>
                <td className="sr-kn">+20 (+1 🌱)</td>
              </tr>
              <tr>
                <td>Đạt bài Vượt thửa</td>
                <td className="sr-kn">+20</td>
              </tr>
              <tr>
                <td>Đạt bài Bắt đầu cấp hoặc Vượt chặng (mỗi cấp × kỹ năng)</td>
                <td className="sr-kn">+20</td>
              </tr>
              <tr>
                <td>Củng cố 1 câu trong Sổ tay (làm đúng khi đến hạn ôn lại)</td>
                <td className="sr-kn">+1</td>
              </tr>
            </tbody>
          </table>
          <p className="sr-note">
            Mỗi bài hoặc mốc chỉ cộng KN <b>một lần</b>, ở lần đạt đầu tiên. Ôn lại bài đã đạt không cộng thêm KN.
          </p>

          <h3 className="sr-h">2. Danh hiệu theo tổng KN</h3>
          <ol className="sr-ranks">
            {RANKS.map((r, i) => (
              <li key={r.ten} className={rank && i + 1 === rank.bac ? "is-now" : rank && i + 1 < rank.bac ? "is-done" : ""}>
                <b>{r.ten}</b>
                <small>{r.min.toLocaleString("vi-VN")} KN</small>
              </li>
            ))}
          </ol>
          <p className="sr-note">KN thể hiện mức chăm chỉ, không dùng để mở cấp HSK.</p>

          <h3 className="sr-h">
            3. Năng lượng ({stats.nang_luong}/{stats.nang_luong_toi_da}) & Chuỗi ngày ({stats.chuoi_ngay ?? 0} ngày)
          </h3>
          <ul className="sr-list">
            <li>
              <b>Trần năng lượng theo cấp HSK:</b> HSK 1 (<b>5</b>) → HSK 2 (<b>6</b>) → HSK 3 (<b>8</b>) → HSK 4 (<b>10</b>); sang ngày mới tự động hồi đầy bình.
            </li>
            <li>
              Học bài mới hoặc làm lại bài chưa đạt: mỗi câu sai hoặc bỏ qua <b>−1 năng lượng</b>. Ôn lại bài đã đạt và
              ôn Sổ tay <b>không tốn năng lượng</b>.
            </li>
            <li>
              Hồi năng lượng trong ngày: Nhiệm vụ ngày (<b>+1 🌱/nhiệm vụ</b>), Ôn Sổ tay đạt ≥ 80% (<b>+1 🌱/lượt</b>, không giới hạn số lần khi chưa đầy), và vượt Kiểm tra cuối thửa 10/10 (<b>+1 🌱</b>).
            </li>
            <li>Chuỗi ngày tăng 1 khi trong ngày bạn nộp xong ít nhất 1 bài có trả lời câu hỏi.</li>
          </ul>
        </RuleDialog>
      )}
    </span>
  );
}
