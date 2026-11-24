import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { getPracticeOverview } from "../api/practiceApi.js";
import "../styles/practice.css";
import { PRACTICE_SKILLS, SKILL_HZ, skillApi } from "../utils/skills.js";

const DEFAULT_TIERS = [
  { cap: "HSK 1", thu_tu: 1, tran: 5 },
  { cap: "HSK 2", thu_tu: 2, tran: 6 },
  { cap: "HSK 3", thu_tu: 3, tran: 8 },
  { cap: "HSK 4", thu_tu: 4, tran: 10 },
];

// Lộ trình Ôn luyện 4 kỹ năng: 4 thẻ kỹ năng trực quan ở trung tâm + 2 thẻ tóm tắt tiến trình thăng cấp & bình năng lượng gọn đẹp
export default function PracticeHomePage() {
  const { token } = useAuth();
  const { data, error, loading } = useRequest((signal) => getPracticeOverview(token, signal), [token]);

  const trinhDo = data?.trinh_do;
  const currentLevel = trinhDo?.ten || "HSK 1";
  const curOrder = trinhDo?.thu_tu || 1;
  const tiers = data?.bang_tran_nang_luong || DEFAULT_TIERS;

  const examMax = trinhDo?.diem_toi_da_thi || 200;
  const examPass = trinhDo?.diem_dat_thi || 120;
  const examBest = trinhDo?.diem_thi_cao_nhat != null ? Math.round(trinhDo.diem_thi_cao_nhat) : 0;
  const examPct = Math.min(100, Math.round((100 * examBest) / Math.max(1, examPass)));
  const skillUnlocked = trinhDo?.so_ky_nang_vuot_cap ?? 0;
  const skillTotal = trinhDo?.tong_ky_nang ?? 4;
  const skillUnlockPct = Math.min(100, Math.round((100 * skillUnlocked) / Math.max(1, skillTotal)));

  return (
    <section className="xc sp-home">
      <header className="xc-head">
        <span className="xc-eyebrow">Lộ trình cá nhân hóa</span>
        <h1>Lộ trình ôn luyện 4 kỹ năng</h1>
        <p>
          Trình độ chính thức: <b>{currentLevel}</b> · Đã mở khóa trọn bộ từ <b>HSK 1 đến {currentLevel}</b> ở cả 4 kỹ năng.
        </p>
      </header>

      {loading && <p className="xc-muted">Đang tải lộ trình...</p>}
      {error && <p role="alert">{error}</p>}

      {data && (
        <>
          {/* 1. BỐN THẺ KỸ NĂNG CHÍNH ĐẶT NGAY TRÊN CÙNG, RÕ RÀNG & NỔI BẬT */}
          <ul className="xc-skills">
            {PRACTICE_SKILLS.map((skill) => {
              const info = data.ky_nang?.find((s) => s.ky_nang === skillApi(skill.slug));
              const pct = info?.so_bai ? Math.round((100 * info.da_xong) / info.so_bai) : 0;
              return (
                <li key={skill.slug}>
                  <Link className={`xc-skill sk-${skill.slug}`} to={`/hoc-vien/on-luyen/${skill.slug}`}>
                    <span className="xc-tile xc-tile--lg" aria-hidden="true">
                      {SKILL_HZ[skill.slug]}
                    </span>
                    <span className="xc-skill__body sp-skill">
                      <span className="sp-skill__head">
                        <h2>{skill.label}</h2>
                        {info?.cap_do?.ten && (
                          <span className="sp-skill__badge">
                            {info.cap_do.ten}
                            {info?.so_bai > 0 ? ` · ${info.da_xong}/${info.so_bai} bài` : ""}
                          </span>
                        )}
                      </span>
                      <p>
                        {info?.bai_tiep
                          ? `${info.bai_tiep.trang_thai === "dang_lam" ? "Đang làm" : "Tiếp tục"}: ${info.bai_tiep.ten}`
                          : info?.so_bai
                            ? "Đã hoàn thành mọi bài ở cấp đang mở"
                            : "Chưa có bài đã xuất bản"}
                      </p>
                      {info?.so_bai > 0 ? (
                        <span
                          className="sp-bar"
                          role="progressbar"
                          aria-valuemin={0}
                          aria-valuemax={info.so_bai}
                          aria-valuenow={info.da_xong}
                          aria-label={`Tiến độ ${skill.label}`}
                        >
                          <i style={{ width: `${pct}%` }} />
                        </span>
                      ) : (
                        <small>Giảng viên chưa xuất bản bài cho phần này.</small>
                      )}
                    </span>
                    <span className="sp-skill__go" aria-hidden="true">
                      <Icon name="arrow" size={18} />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>

          {/* 2. HAI THẺ TÓM TẮT TRỰC QUAN: ĐIỀU KIỆN THĂNG CẤP & BÌNH NĂNG LƯỢNG / KN */}
          <div className={`sp-meta-grid${trinhDo?.cap_tiep_theo ? "" : " is-single"}`}>
            {trinhDo?.cap_tiep_theo && (
              <article className="sp-meta-card">
                <div className="sp-meta-card__top">
                  <div>
                    <span className="xc-eyebrow">Mục tiêu tiếp theo</span>
                    <h2>
                      Nâng từ {currentLevel} lên {trinhDo.cap_tiep_theo}
                    </h2>
                  </div>
                  {trinhDo.tran_nang_luong_tiep && (
                    <span className="sp-pill sp-pill--teal">
                      Mở bình {trinhDo.tran_nang_luong_tiep}/{trinhDo.tran_nang_luong_tiep} 🌱
                    </span>
                  )}
                </div>

                <p className="sp-meta-card__sub">Đạt 1 trong 2 cột mốc dưới đây để mở khóa toàn diện {trinhDo.cap_tiep_theo}:</p>

                <div className="sp-ways">
                  <div className="sp-way">
                    <div className="sp-way__row">
                      <b>Cách 1 · Thi thử {currentLevel}</b>
                      <span>
                        {trinhDo.diem_thi_cao_nhat != null ? `${examBest}/${examMax}đ` : "Chưa thi"} · Cần ≥ {examPass}đ
                      </span>
                    </div>
                    <span className="sp-bar sp-bar--sm" aria-hidden="true">
                      <i style={{ width: `${examPct}%` }} />
                    </span>
                  </div>

                  <div className="sp-way">
                    <div className="sp-way__row">
                      <b>Cách 2 · Vượt cấp 4 kỹ năng</b>
                      <span>
                        Đã mở {skillUnlocked}/{skillTotal} kỹ năng
                      </span>
                    </div>
                    <span className="sp-bar sp-bar--sm" aria-hidden="true">
                      <i style={{ width: `${skillUnlockPct}%` }} />
                    </span>
                  </div>
                </div>

                <div className="sp-meta-card__foot">
                  <Link className="xc-btn xc-btn--sm" to="/hoc-vien/thi-thu">
                    Thi thử thăng cấp <Icon name="arrow" size={16} />
                  </Link>
                </div>
              </article>
            )}

            <article className="sp-meta-card">
              <div className="sp-meta-card__top">
                <div>
                  <span className="xc-eyebrow" style={{ color: "var(--coral-ink)" }}>
                    Cơ chế Năng lượng & KN
                  </span>
                  <h2>Bình năng lượng theo trình độ</h2>
                </div>
                <span className="sp-pill sp-pill--good">
                  Hiện có {data.nang_luong}/{data.nang_luong_toi_da} 🌱
                </span>
              </div>

              <div className="sp-tiers" aria-label="Trần năng lượng theo cấp HSK">
                {tiers.map((t) => {
                  const isCurrent = t.thu_tu === curOrder;
                  const isUnlocked = t.thu_tu <= curOrder;
                  return (
                    <div key={t.cap} className={`sp-tier${isCurrent ? " is-current" : isUnlocked ? " is-open" : ""}`}>
                      <small>{t.cap}</small>
                      <b>{t.tran} 🌱</b>
                    </div>
                  );
                })}
              </div>

              <div className="sp-rewards">
                <div className="sp-reward">
                  <span>Bài thường (5/5)</span>
                  <b>+10 KN</b>
                </div>
                <div className="sp-reward">
                  <span>Cuối thửa (10/10)</span>
                  <b>+20 KN · +1 🌱</b>
                </div>
                <div className="sp-reward">
                  <span>Vượt thửa / Mở cấp</span>
                  <b>+20 KN</b>
                </div>
                <div className="sp-reward">
                  <span>Ôn Sổ tay (≥ 80%)</span>
                  <b>+1 🌱 / lượt</b>
                </div>
              </div>

              <p className="sp-meta-card__note">
                Sang ngày mới tự hồi đầy bình · Ôn bài Đã xong, Sổ tay & Thi thử hoàn toàn miễn phí năng lượng.
              </p>
            </article>
          </div>
        </>
      )}
    </section>
  );
}
