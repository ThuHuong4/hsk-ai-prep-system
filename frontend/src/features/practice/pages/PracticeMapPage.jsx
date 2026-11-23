import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { getSkillPath, startLesson, startLevelTest, startSkip } from "../api/practiceApi.js";
import LevelTestCard from "../components/LevelTestCard.jsx";
import PathMap from "../components/PathMap.jsx";
import { findSkill, skillApi } from "../utils/skills.js";
import "../styles/practice.css";
import "../styles/mapLayout.css";

export default function PracticeMapPage() {
  const { kyNang } = useParams();
  const [params, setParams] = useSearchParams();
  const skill = findSkill(kyNang);
  const capParam = Number(params.get("cap")) || null;
  const { token } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const { data, error, loading } = useRequest(
    skill ? (signal) => getSkillPath(token, skillApi(skill.slug), capParam, signal) : null,
    [token, kyNang, capParam]
  );

  async function begin(slot) {
    if (slot.luot_dang_lam) { navigate(`/on-luyen/bai/${slot.luot_dang_lam}`); return; }
    setBusy(true);
    setNotice("");
    try {
      const res = await startLesson(token, slot.ma_goc_id);
      navigate(`/on-luyen/bai/${res.luot_id}`);
    } catch (err) {
      setNotice(err?.message || "Không mở được bài");
      setBusy(false);
    }
  }

  async function skip(land) {
    setBusy(true);
    setNotice("");
    try {
      const res = await startSkip(token, land.ma_goc_id);
      navigate(`/on-luyen/vuot/${res.luot_id}`);
    } catch (err) {
      setNotice(err?.message || "Không mở được kiểm tra vượt");
      setBusy(false);
    }
  }

  async function levelTest(test) {
    if (test.luot_dang_lam) { navigate(`/on-luyen/vuot/${test.luot_dang_lam}`); return; }
    setBusy(true);
    setNotice("");
    try {
      const res = await startLevelTest(token, data.cap_do.id, skillApi(skill.slug), test.loai === "vuot_chang" ? "vuot-chang" : "bat-dau-cap");
      navigate(`/on-luyen/vuot/${res.luot_id}`);
    } catch (err) {
      setNotice(err?.message || "Không mở được bài kiểm tra");
      setBusy(false);
    }
  }

  if (!skill) return <section className="xc"><p role="alert">Kỹ năng không hợp lệ.</p></section>;
  const next = data?.bai_tiep;
  const current = next?.ma_goc_id;

  return (
    <section className="xc sp-page">
      <div className="sp-top2">
        <Link className="sp-back" to="/hoc-vien/on-luyen" aria-label="Chọn kỹ năng khác"><Icon name="arrowLeft" /></Link>
        <h1>{skill.label}{data?.cap_do && <small> · {data.cap_do.ten}</small>}</h1>
      </div>
      {loading && <p className="xc-muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <div className="sp-tabs" role="tablist" aria-label="Cấp HSK">
            {data.cap.map((c) => (
              <button key={c.id} type="button" role="tab" aria-selected={data.cap_do?.id === c.id}
                className={`sp-tab${c.mo ? "" : " is-locked"}`} onClick={() => setParams({ cap: String(c.id) })}>
                <b>{c.ten}</b>
                <small>{!c.mo ? "Chưa mở" : c.so_bai ? `${c.da_xong}/${c.so_bai} bài` : "Chưa có bài"}</small>
              </button>
            ))}
          </div>
          {notice && <p role="alert">{notice}</p>}
          {!data.cap_do?.mo ? (
            <>
              <LevelTestCard test={data.kiem_tra_cap} level={data.cap_do} skillLabel={skill.label} busy={busy} onStart={levelTest} />
              {data.thua.length > 0 && (
                <PathMap lands={data.thua} currentId={null} onStart={begin} busy={busy}
                  lockText={`${data.cap_do.ten} chưa mở. Làm kiểm tra bắt đầu cấp hoặc vượt cấp ở cấp trước để mở.`} />
              )}
            </>
          ) : data.thua.length === 0 ? (
            <div className="xc-empty"><p>{skill.label} chưa có thửa nào được xuất bản ở cấp này.</p></div>
          ) : (
            <>
              <PathMap lands={data.thua} currentId={current} onStart={begin} onSkip={skip} busy={busy} />
              <LevelTestCard test={data.kiem_tra_cap} level={data.cap_do} skillLabel={skill.label} busy={busy} onStart={levelTest} />
            </>
          )}
        </>
      )}
    </section>
  );
}
