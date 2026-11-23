import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useRequest } from "../../../../shared/api/useRequest.js";
import Icon from "../../../../shared/components/Icon.jsx";
import { useAuth } from "../../../auth/context/AuthContext.jsx";
import { ROLE } from "../../../auth/utils/roles.js";
import "../../../exam_catalog/styles/catalog.css";
import { PRACTICE_SKILLS, SKILL_HZ, skillApi } from "../../utils/skills.js";
import "../../styles/practice.css";
import "../../styles/mapLayout.css";
import { getGuestOverview } from "../api/guestPracticeApi.js";
import "../styles/guestPractice.css";
import { GUEST_MAX_ENERGY, applyGuestProgress, nextLesson, readGuest } from "../utils/guestProgress.js";

// Ôn luyện cho Khách: giống trang Học viên (chọn kỹ năng, không chọn cấp trước)
export default function GuestPracticeHomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [guest] = useState(readGuest);
  const isStudent = user?.vai_tro === ROLE.HOC_VIEN;
  const { data, error, loading } = useRequest(isStudent ? null : (signal) => getGuestOverview(signal), [isStudent]);

  if (isStudent) return <Navigate to="/hoc-vien/on-luyen" replace />;

  return (
    <section className="xc">
      <header className="xc-head">
        <div className="sp-top2">
          <h1>Ôn luyện</h1>
          <span className="sp-stat sp-stat--energy" title="Năng lượng học thử hôm nay">
            <Icon name="sprout" size={18} /><b>{guest.nang_luong}/{GUEST_MAX_ENERGY}</b>
          </span>
        </div>
        <p>Mỗi kỹ năng có tiến độ riêng. Mỗi cấp gồm nhiều thửa, mỗi thửa là một chủ đề với 4 bài và 1 kiểm tra cuối thửa.</p>
        <p className="gp-line">
          Bạn đang học thử, tiến độ không lưu vào tài khoản.{" "}
          <button type="button" className="gp-link" onClick={() => navigate("/dang-nhap", { state: { from: "/on-luyen" } })}>Đăng nhập để lưu</button>
        </p>
      </header>
      {loading && <p className="xc-muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <ul className="xc-skills">
          {PRACTICE_SKILLS.map((skill) => {
            const info = data.ky_nang?.find((s) => s.ky_nang === skillApi(skill.slug));
            const lands = applyGuestProgress(info?.thua ?? [], guest);
            const slots = lands.flatMap((l) => l.o).filter((o) => o.trang_thai !== "chua_xuat_ban");
            const done = slots.filter((o) => o.trang_thai === "da_xong").length;
            const next = nextLesson(lands);
            const pct = slots.length ? Math.round((100 * done) / slots.length) : 0;
            return (
              <li key={skill.slug}>
                <Link className={`xc-skill sk-${skill.slug}`} to={`/on-luyen/${skill.slug}`}>
                  <span className="xc-tile xc-tile--lg" aria-hidden="true">{SKILL_HZ[skill.slug]}</span>
                  <span className="xc-skill__body sp-skill">
                    <h2>{skill.label}</h2>
                    <p>
                      <b>{info?.cap_do?.ten ?? "—"}</b>
                      {" · "}
                      {next ? `${next.trang_thai === "chua_dat" ? "Làm lại" : "Tiếp tục"}: ${next.ten}`
                        : slots.length ? "Đã xong mọi bài đang mở" : "Chưa có bài đã xuất bản"}
                    </p>
                    {slots.length > 0 ? (
                      <>
                        <span className="sp-bar" role="progressbar" aria-valuemin={0} aria-valuemax={slots.length} aria-valuenow={done}
                          aria-label={`Tiến độ ${skill.label}`}><i style={{ width: `${pct}%` }} /></span>
                        <small>{info.cap_do.ten}: đã học {done}/{slots.length} bài</small>
                      </>
                    ) : (
                      <small>Giảng viên chưa xuất bản bài cho phần này.</small>
                    )}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
