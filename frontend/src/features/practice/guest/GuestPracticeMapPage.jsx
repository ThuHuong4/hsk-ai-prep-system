import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { ROLE } from "../../auth/utils/roles.js";
import "../../exam_catalog/styles/catalog.css";
import PathMap from "../components/PathMap.jsx";
import { findSkill, skillApi } from "../skills.js";
import "../styles/practice.css";
import "../styles/mapLayout.css";
import { getGuestPath } from "./guestPracticeApi.js";
import { GUEST_MAX_ENERGY, applyGuestProgress, nextLesson, readGuest } from "./guestProgress.js";
import "./guestPractice.css";

// Bản đồ thửa cho Khách: giống Học viên (/on-luyen/:kyNang?cap=), tiến độ chỉ lưu trên trình duyệt
export default function GuestPracticeMapPage() {
  const { kyNang } = useParams();
  const [params] = useSearchParams();
  const capParam = Number(params.get("cap")) || null;
  const skill = findSkill(kyNang);
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notice, setNotice] = useState("");
  const [guest] = useState(readGuest);
  const isStudent = user?.vai_tro === ROLE.HOC_VIEN;
  const { data, error, loading } = useRequest(
    !skill || isStudent ? null : (signal) => getGuestPath(skillApi(skill.slug), capParam, signal),
    [kyNang, capParam, isStudent]
  );

  // Học viên đã đăng nhập → bản đồ thật có lưu tiến độ
  if (isStudent && skill) {
    return <Navigate to={`/hoc-vien/on-luyen/${skill.slug}${capParam ? `?cap=${capParam}` : ""}`} replace />;
  }

  const here = location.pathname + location.search;
  const login = () => navigate("/dang-nhap", { state: { from: here } });

  function begin(slot) {
    if (slot.trang_thai !== "da_xong" && readGuest().nang_luong <= 0) {
      setNotice("Hết năng lượng hôm nay. Đăng nhập để học tiếp và lưu tiến độ.");
      return;
    }
    navigate(`/on-luyen/hoc-thu/${slot.ma_goc_id}`, { state: { from: here } });
  }

  if (!skill) {
    return (
      <section className="xc">
        <Link className="xc-back" to="/on-luyen"><Icon name="arrowLeft" />Kỹ năng</Link>
        <p role="alert">Kỹ năng không hợp lệ.</p>
      </section>
    );
  }

  const lands = data ? applyGuestProgress(data.thua, guest) : [];
  const next = nextLesson(lands);

  return (
    <section className="xc sp-page">
      <div className="sp-top2">
        <Link className="sp-back" to="/on-luyen" aria-label="Chọn kỹ năng khác"><Icon name="arrowLeft" /></Link>
        <h1>{skill.label}{data?.cap_do && <small> · {data.cap_do.ten}</small>}</h1>
        <span className="sp-stat sp-stat--energy" title="Năng lượng học thử hôm nay">
          <Icon name="sprout" size={18} /><b>{guest.nang_luong}/{GUEST_MAX_ENERGY}</b>
        </span>
      </div>
      {loading && <p className="xc-muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <nav className="sp-tabs" aria-label="Cấp HSK">
            {data.cap.map((c) => (c.mo ? (
              <Link key={c.id} className="sp-tab" to={`/on-luyen/${skill.slug}?cap=${c.id}`} aria-selected={c.id === data.cap_do?.id}>
                <b>{c.ten}</b><small>{c.so_bai ? `${c.so_bai} bài` : "Chưa có bài"}</small>
              </Link>
            ) : (
              <span key={c.id} className="sp-tab" aria-disabled="true"><b>{c.ten}</b><small>Chưa mở</small></span>
            )))}
          </nav>
          <p className="gp-line">Bạn đang học thử, tiến độ không lưu vào tài khoản. <button type="button" className="gp-link" onClick={login}>Đăng nhập để lưu</button></p>
          {notice && <p role="alert">{notice}</p>}
          {!data.cap_do?.mo ? (
            <div className="xc-empty"><p>{skill.label} chưa mở ở cấp này.</p></div>
          ) : lands.length === 0 ? (
            <div className="xc-empty"><p>{skill.label} chưa có thửa nào được xuất bản ở cấp này.</p></div>
          ) : (
            <PathMap lands={lands} currentId={next?.ma_goc_id} onStart={begin} onSkip={login} busy={false} />
          )}
        </>
      )}
    </section>
  );
}
