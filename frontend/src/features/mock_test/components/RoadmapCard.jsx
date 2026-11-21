import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { startLesson } from "../../practice/api/practiceApi.js";
import { fetchMaterialUrl, getRoadmap } from "../api/roadmapApi.js";
import "../styles/roadmap.css";

const SKILL = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
const DANG = {
  chon_mot: "Chọn một đáp án", dung_sai: "Đúng/Sai", chon_bo_chung: "Chọn từ bộ chung",
  sap_xep: "Sắp xếp câu", dien_chu: "Điền chữ", viet_mo: "Viết đoạn",
};

function Trend({ now, before }) {
  if (!before) return null;
  const a = before.tong ? before.dung / before.tong : 0;
  const b = now.tong ? now.dung / now.tong : 0;
  const cls = b > a + 0.001 ? "is-up" : b < a - 0.001 ? "is-down" : "";
  const arrow = cls === "is-up" ? "↑" : cls === "is-down" ? "↓" : "=";
  return <span className={`rm-trend ${cls}`} title="So với lượt thi trước cùng cấp">lần trước {before.dung}/{before.tong} {arrow}</span>;
}

function Bars({ groups }) {
  if (!groups?.length) return null;
  return (
    <ul className="rm-bars" aria-label="Tỷ lệ đúng theo kỹ năng và dạng câu">
      {groups.map((g) => (
        <li key={`${g.ky_nang}-${g.dang}`} className={g.ty_le < 0.6 ? "is-weak" : ""}>
          <span className="rm-bars__name">{SKILL[g.ky_nang]} · {DANG[g.dang] || g.dang}</span>
          <span className="rm-bars__track" aria-hidden="true"><span style={{ width: `${Math.round(g.ty_le * 100)}%` }} /></span>
          <span className="rm-bars__val">{g.dung}/{g.tong}</span>
        </li>
      ))}
    </ul>
  );
}

function jumpTo(no) {
  document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
}

export default function RoadmapCard({ luotId }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: true, data: null, error: "" });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let alive = true;
    setState({ loading: true, data: null, error: "" });
    getRoadmap(token, luotId)
      .then((data) => alive && setState({ loading: false, data, error: "" }))
      .catch((err) => alive && setState({ loading: false, data: null, error: err?.message || "Không tải được gợi ý lộ trình" }));
    return () => { alive = false; };
  }, [token, luotId]);

  async function openLesson(maGoc) {
    if (busy) return;
    setBusy(true);
    setNotice("");
    try {
      const res = await startLesson(token, maGoc);
      navigate(`/on-luyen/bai/${res.luot_id}`);
    } catch (err) {
      setNotice(err?.message || "Không mở được bài ôn");
      setBusy(false);
    }
  }

  async function openMaterial(id) {
    setNotice("");
    const tab = window.open("", "_blank"); // mở tab ngay khi bấm để trình duyệt không chặn
    try {
      const url = await fetchMaterialUrl(token, id);
      if (tab) tab.location.href = url;
      else window.location.href = url;
    } catch (err) {
      tab?.close();
      setNotice(err?.message || "Không mở được tài liệu");
    }
  }

  const { loading, data, error } = state;
  return (
    <section className="rm-card" aria-labelledby="rm-title" aria-busy={loading}>
      <header className="rm-head">
        <img src={xiangFace} alt="" className="rm-head__face" />
        <div>
          <h2 id="rm-title">Xiang gợi ý lộ trình</h2>
          <p className="lv-help">
            Phân tích từ bài thi này, chỉ trỏ tới bài ôn và tài liệu đang có.
            {data?.lan_truoc && <> So sánh với lượt trước: {data.lan_truoc.ten_de}.</>}
          </p>
        </div>
      </header>

      {loading && <p className="lv-muted">Xiang đang phân tích bài làm…</p>}
      {error && <p role="alert" className="lv-alert">{error}</p>}

      {data && (
        <>
          <Bars groups={data.nhom} />
          {data.ghi_chu && <p className="rm-note">{data.ghi_chu}</p>}
          {data.goi_y.length > 0 && (
            <ol className="rm-list">
              {data.goi_y.map((g, i) => (
                <li key={`${g.ky_nang}-${g.dang}`} className="rm-plan">
                  <div className="rm-plan__head">
                    <span className="rm-plan__no">{i + 1}</span>
                    <div className="rm-plan__title">
                      <h3>{SKILL[g.ky_nang]} · {DANG[g.dang] || g.dang}</h3>
                      {g.phan_ten.length > 0 && <p>{g.phan_ten.join(" · ")}</p>}
                    </div>
                    <div className="rm-plan__score">
                      <b>{g.dung}/{g.tong}</b>
                      <Trend now={g} before={g.truoc} />
                    </div>
                  </div>

                  {g.ghi_chu_cap && (
                    <p className="rm-level">
                      {g.ghi_chu_cap}
                      {g.mo_cap && <> <Link to={`/hoc-vien/on-luyen/${g.mo_cap.ky_nang}?cap=${g.mo_cap.cap_do_id}`}>Mở cấp này →</Link></>}
                    </p>
                  )}

                  <ol className="rm-steps">
                    {g.cau_sai.length > 0 && (
                      <li className="rm-step">
                        <div className="rm-step__body">
                          <p className="rm-step__name">Xem lại {g.cau_sai.length} câu sai trong đề này</p>
                          <div className="rm-chips">
                            {g.cau_sai.map((n) => (
                              <button key={n} type="button" className="rm-chip" onClick={() => jumpTo(n)} aria-label={`Đến câu ${n}`}>{n}</button>
                            ))}
                          </div>
                        </div>
                      </li>
                    )}
                    {g.buoc.map((s) => (
                      <li key={s.thu_tu} className="rm-step">
                        <div className="rm-step__body">
                          <p className="rm-step__why">{s.ly_do}</p>
                          <p className="rm-step__name">
                            {s.dich.loai === "bai"
                              ? <>Bài ôn: <b>{s.dich.thua} · {s.dich.ten}</b>{s.dich.cap ? ` (${s.dich.cap})` : ""}</>
                              : <>Cẩm nang: <b>{s.dich.ten}</b></>}
                          </p>
                        </div>
                        {s.dich.kha_dung ? (
                          s.dich.loai === "bai"
                            ? <button type="button" className="xbtn rm-step__go" disabled={busy} onClick={() => openLesson(s.dich.ma_goc_id)}>Ôn ngay</button>
                            : <button type="button" className="xbtn xbtn--ghost rm-step__go" onClick={() => openMaterial(s.dich.id)}>Mở tài liệu</button>
                        ) : <span className="rm-step__off">Đã ngừng đăng</span>}
                      </li>
                    ))}
                    {g.buoc.length === 0 && <li className="rm-step"><p className="rm-step__why">Chưa có bài ôn hay tài liệu phù hợp cho nhóm này.</p></li>}
                    {g.hoc_them?.length > 0 && (
                      <li className="rm-step">
                        <div className="rm-step__body">
                          <p className="rm-step__name">Học thêm từ nguồn bên ngoài (mở tab mới)</p>
                          <ul className="rm-links">
                            {g.hoc_them.map((x) => (
                              <li key={x.url}>
                                <a href={x.url} target="_blank" rel="noopener noreferrer">{x.ten} ↗</a>
                                <span>{x.mo_ta}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </li>
                    )}
                  </ol>
                </li>
              ))}
            </ol>
          )}
          {notice && <p role="alert" className="lv-alert">{notice}</p>}
          {data.goi_y.length > 0 && <p className="lv-help rm-foot">Ôn xong các bước trên rồi thi một đề khác cùng cấp: Xiang sẽ so sánh từng nhóm với lần này.</p>}
        </>
      )}
    </section>
  );
}
