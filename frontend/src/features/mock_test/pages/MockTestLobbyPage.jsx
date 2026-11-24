/**
 * Phòng chờ Thi thử HSK trên máy tính (`/hoc-vien/thi-thu` — chuẩn HSK iBT / 汉考国际机考考前须知).
 * - Không hiển thị HSK 1–4 để tự chọn và không tiết lộ tên cấp độ trước giờ thi.
 * - Đầy đủ bước Kiểm tra thiết bị âm thanh (试音), 6 quy chế phòng thi chuẩn HSK thật,
 *   và ô tích cam kết bắt buộc trước khi mở khóa nút "Bắt đầu thi thử".
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { getExamLobby, startRandomExam } from "../api/mockTestApi.js";
import "../styles/mockTest.css";

const SKILL_VI = { nghe: "Nghe hiểu (听力)", doc: "Đọc hiểu (阅读)", viet: "Viết (书写)" };

function playSpeakerTestTone() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return false;
  const ctx = new AudioCtx();
  const notes = [523.25, 659.25, 783.99];
  notes.forEach((freq, idx) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    const startAt = ctx.currentTime + idx * 0.18;
    gain.gain.setValueAtTime(0.001, startAt);
    gain.gain.exponentialRampToValueAtTime(0.18, startAt + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.001, startAt + 0.22);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(startAt);
    osc.stop(startAt + 0.24);
  });
  setTimeout(() => ctx.close().catch(() => {}), 900);
  return true;
}

export default function MockTestLobbyPage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const { data, error, loading } = useRequest((signal) => getExamLobby(token, signal), [token]);
  const [starting, setStarting] = useState(false);
  const [audioChecked, setAudioChecked] = useState(false);
  const [agreedRules, setAgreedRules] = useState(false);
  const [testingSound, setTestingSound] = useState(false);
  const [notice, setNotice] = useState("");

  function handleAudioTest() {
    if (testingSound) return;
    setTestingSound(true);
    try {
      playSpeakerTestTone();
      setTimeout(() => {
        setAudioChecked(true);
        setTestingSound(false);
      }, 650);
    } catch {
      setAudioChecked(true);
      setTestingSound(false);
    }
  }

  async function handleStart() {
    if (starting) return;
    if (data?.luot_dang_lam) {
      document.documentElement.requestFullscreen?.().catch(() => {});
      navigate(`/thi-thu/lam-bai/${data.luot_dang_lam.luot_id}`);
      return;
    }
    if (!agreedRules) return;
    setStarting(true);
    setNotice("");
    try {
      document.documentElement.requestFullscreen?.().catch(() => {});
      const res = await startRandomExam(token);
      navigate(`/thi-thu/lam-bai/${res.luot_id}`);
    } catch (err) {
      if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
      setNotice(err?.message || "Hiện chưa mở được bài thi thử, bạn vui lòng thử lại sau.");
      setStarting(false);
    }
  }

  const activeExam = data?.luot_dang_lam;
  const skillsText = (data?.ky_nang ?? ["nghe", "doc"]).map((k) => SKILL_VI[k] || k).join(" → ");

  return (
    <section className="xc ibt-lobby-page">
      <div className="ibt-lobby">
        <header className="ibt-lobby__banner">
          <div className="ibt-lobby__kicker">
            <span className="ibt-seal-badge">汉语水平考试 · 网络机考系统</span>
            <Link className="ibt-hist-link" to="/hoc-vien/lich-su-thi">
              <Icon name="doc" size={16} /> Lịch sử thi thử
            </Link>
          </div>
          <h1>Phòng thi thử HSK trực tuyến</h1>
          <p>
            Hệ thống tự động rút ngẫu nhiên 1 bộ đề bảo mật tương ứng với trình độ hiện tại của bạn ngay khi mở đề.
            Toàn bộ quy trình điều hướng, khóa phần thi và phát âm thanh tuân thủ nghiêm ngặt chuẩn thi HSK trên máy tính (HSK iBT).
          </p>
        </header>

        {loading && <p className="xc-muted">Đang kiểm tra trạng thái phòng thi…</p>}
        {error && <p role="alert">{error}</p>}

        {data && (
          <div className="ibt-lobby__grid">
            {/* Cột trái: Thông tin ca thi & Kiểm tra âm thanh (试音) */}
            <div className="ibt-pass-card">
              <div className="ibt-pass-card__head">
                <Icon name="user" size={18} />
                <h2>Thông tin thí sinh & Ca thi</h2>
              </div>

              <dl className="ibt-meta-list">
                <div>
                  <dt>Họ tên thí sinh</dt>
                  <dd>{user?.ho_ten || "Học viên"}</dd>
                </div>
                <div>
                  <dt>Cơ chế phát đề</dt>
                  <dd>Ngẫu nhiên bảo mật theo trình độ hiện tại</dd>
                </div>
                <div>
                  <dt>Cấu trúc bài thi</dt>
                  <dd>
                    {data.so_cau_chuan} câu tính điểm · {data.thoi_luong_phut} phút
                  </dd>
                </div>
                <div>
                  <dt>Trình tự phần thi</dt>
                  <dd>{skillsText}</dd>
                </div>
                <div>
                  <dt>Điểm chuẩn xét Đạt</dt>
                  <dd>
                    Từ {data.diem_dat_thi} trên {data.diem_toi_da_thi} điểm trở lên
                  </dd>
                </div>
                <div>
                  <dt>Phím tắt làm bài</dt>
                  <dd>← / → chuyển câu · A–F (1–6) chọn · M gắn cờ</dd>
                </div>
              </dl>

              {data.ten_cap_tiep_theo ? (
                <div
                  style={{
                    padding: "13px 15px",
                    borderRadius: 15,
                    background: "var(--teal-soft)",
                    border: "1px solid color-mix(in srgb, var(--teal) 38%, transparent)",
                    color: "var(--ink)",
                    fontSize: 13.8,
                    lineHeight: 1.5,
                  }}
                >
                  <strong style={{ display: "block", color: "var(--teal-ink)", marginBottom: 4 }}>
                    Quy định nâng trình độ từ {data.ten_trinh_do_hien_tai} lên {data.ten_cap_tiep_theo}
                  </strong>
                  <span>
                    Nếu kết quả bài thi thử này đạt từ{" "}
                    <b>
                      {data.diem_dat_thi} trên {data.diem_toi_da_thi} điểm trở lên
                    </b>
                    , tài khoản của bạn sẽ được <b>chính thức nâng lên Trình độ {data.ten_cap_tiep_theo}</b> (tự động mở
                    khóa toàn bộ lộ trình ôn luyện {data.ten_cap_tiep_theo} ở cả 4 kỹ năng và nâng đề thi thử lần sau
                    sang {data.ten_cap_tiep_theo}).
                  </span>
                </div>
              ) : null}

              <div className={`ibt-audio-check${audioChecked ? " is-ok" : ""}`}>
                <div>
                  <strong>
                    <Icon name="audio" size={17} /> Bước 1: Kiểm tra loa / tai nghe (试音)
                  </strong>
                  <p>
                    Trong phòng thi thật, băng Nghe phát tự động không cho phép kéo tua lại. Hãy kiểm tra loa hoặc tai nghe ngay trước khi bắt đầu.
                  </p>
                </div>
                <button
                  type="button"
                  className="xc-btn xc-btn--plain xc-btn--sm"
                  onClick={handleAudioTest}
                  disabled={testingSound}
                >
                  {testingSound
                    ? "Đang phát âm báo…"
                    : audioChecked
                      ? "✓ Thiết bị âm thanh hoạt động tốt (Thử lại)"
                      : "Phát âm thanh kiểm tra loa"}
                </button>
              </div>
            </div>

            {/* Cột phải: 6 Quy chế chuẩn HSK máy tính thật & Cam kết bắt đầu */}
            <div className="ibt-rules-card">
              {activeExam ? (
                <div className="ibt-resume-alert">
                  <strong>Đang có ca thi chưa nộp bài</strong>
                  <p>
                    Đồng hồ máy chủ vẫn đang chạy (còn khoảng{" "}
                    <b>{Math.max(1, Math.ceil(activeExam.con_lai_giay / 60))} phút</b>). Bấm nút bên dưới để quay lại đúng câu và phần thi đang làm dở.
                  </p>
                </div>
              ) : null}

              <h2>Quy chế phòng thi HSK trên máy tính</h2>
              <ul className="xc-checks">
                <li>
                  <Icon name="check" />
                  <span>
                    <b>Khóa phần thi một chiều (严禁跨区):</b> Làm lần lượt theo đúng thứ tự <b>{skillsText}</b>. Khi đang thi Nghe không được mở trước phần sau; đã chốt chuyển sang phần kế tiếp sẽ <b>khóa vĩnh viễn phần trước</b> (không thể quay lại sửa).
                  </span>
                </li>
                <li>
                  <Icon name="check" />
                  <span>
                    <b>Quy định âm thanh phần Nghe:</b> Băng nghe phát tốc độ chuẩn 1.0x, <b>không hỗ trợ tạm dừng hay kéo thanh tua lại</b> giống hệt phòng thi HSK quốc tế.
                  </span>
                </li>
                <li>
                  <Icon name="check" />
                  <span>
                    <b>Đồng hồ máy chủ chạy liên tục & Tự động lưu:</b> Đáp án lưu ngay khi chọn. Nếu bấm <code>F5</code> hoặc thoát trang vào lại, đồng hồ vẫn tiếp tục đếm ngược và giữ nguyên đúng bộ đề đang thi.
                  </span>
                </li>
                <li>
                  <Icon name="check" />
                  <span>
                    <b>Điều hướng trong phần đang mở:</b> Trong nội bộ một phần kỹ năng, thí sinh tự do chuyển câu bằng Phiếu trả lời điện tử, phím mũi tên <code>← / →</code>, chọn nhanh bằng <code>1–6 / A–F</code> và gắn cờ xem lại bằng phím <code>M</code>.
                  </span>
                </li>
                <li>
                  <Icon name="check" />
                  <span>
                    <b>Điều kiện nộp bài & Thu bài tự động:</b> Chuyển phần hoặc nộp bài sớm yêu cầu hoàn thành đủ các câu tính điểm; khi đồng hồ chạm <b>00:00</b> hệ thống tự thu bài ngay lập tức.
                  </span>
                </li>
                <li>
                  <Icon name="check" />
                  <span>
                    <b>Giám sát phòng thi & Chống gian lận:</b> Bài thi tự bật chế độ <b>Toàn màn hình</b>, khóa nút Back,
                    chặn sao chép đề và chặn dán văn bản vào bài Viết. Nếu chuyển sang tab khác / thu nhỏ cửa sổ đủ{" "}
                    <b>3 lần (切屏)</b>, hệ thống sẽ <b>tự động lập biên bản và thu bài ngay lập tức</b>.
                  </span>
                </li>
              </ul>

              {notice && <p role="alert">{notice}</p>}

              <div className="ibt-start-box">
                {!activeExam && (
                  <label className="ibt-agree-row">
                    <input
                      type="checkbox"
                      checked={agreedRules}
                      onChange={(e) => setAgreedRules(e.target.checked)}
                    />
                    <span>
                      Tôi đã kiểm tra âm thanh và xác nhận tuân thủ nghiêm túc các quy chế phòng thi HSK trên.
                    </span>
                  </label>
                )}

                <button
                  type="button"
                  className={`xc-btn xc-btn--block ${activeExam ? "xc-btn--coral" : "xc-btn--exam"}`}
                  disabled={starting || !data.san_sang_thi || (!activeExam && !agreedRules)}
                  onClick={handleStart}
                >
                  {starting
                    ? "Đang mở niêm phong đề thi…"
                    : activeExam
                      ? "Quay lại phòng thi đang làm"
                      : data.san_sang_thi
                        ? "Bắt đầu thi thử"
                        : "Chưa có bộ đề phù hợp"}{" "}
                  <Icon name="arrow" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
