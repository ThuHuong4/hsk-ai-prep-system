import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { getPracticeOverview } from "../api/practiceApi.js";
import { PRACTICE_SKILLS, SKILL_HZ, skillApi } from "../utils/skills.js";
import "../styles/practice.css";

// Ôn luyện: mỗi kỹ năng một lộ trình riêng (mục 4.1)
export default function PracticeHomePage() {
  const { token } = useAuth();
  const { data, error, loading } = useRequest((signal) => getPracticeOverview(token, signal), [token]);

  return (
    <section className="xc">
      <header className="xc-head">
        <h1>Ôn luyện</h1>
      </header>
      {loading && <p className="xc-muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <ul className="xc-skills">
          {PRACTICE_SKILLS.map((skill) => {
            const info = data.ky_nang?.find((s) => s.ky_nang === skillApi(skill.slug));
            const pct = info?.so_bai ? Math.round((100 * info.da_xong) / info.so_bai) : 0;
            return (
              <li key={skill.slug}>
                <Link className={`xc-skill sk-${skill.slug}`} to={`/hoc-vien/on-luyen/${skill.slug}`}>
                  <span className="xc-tile xc-tile--lg" aria-hidden="true">{SKILL_HZ[skill.slug]}</span>
                  <span className="xc-skill__body sp-skill">
                    <h2>{skill.label}</h2>
                    <p>
                      <b>{info?.cap_do?.ten ?? "—"}</b>
                      {" · "}
                      {info?.bai_tiep ? `${info.bai_tiep.trang_thai === "dang_lam" ? "Đang làm" : "Tiếp tục"}: ${info.bai_tiep.ten}`
                        : info?.so_bai ? "Đã xong mọi bài đang mở" : "Chưa có bài đã xuất bản"}
                    </p>
                    {info?.so_bai > 0 && (
                      <>
                        <span className="sp-bar" role="progressbar" aria-valuemin={0} aria-valuemax={info.so_bai} aria-valuenow={info.da_xong}
                          aria-label={`Tiến độ ${skill.label}`}><i style={{ width: `${pct}%` }} /></span>
                        <small>{info.cap_do.ten}: đã học {info.da_xong}/{info.so_bai} bài</small>
                      </>
                    )}
                    {!info?.so_bai && <small>Giảng viên chưa xuất bản bài cho phần này.</small>}
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
