import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { startLesson } from "../../practice/api/practiceApi.js";
import { fetchMaterialUrl } from "../../study_materials/api/materialsApi.js";
import { getRoadmap } from "../api/roadmapApi.js";
import "../styles/roadmap.css";

const SKILL = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };
const DANG = {
  chon_mot: "Chọn một đáp án",
  dung_sai: "Đúng/Sai",
  chon_bo_chung: "Chọn từ bộ chung",
  sap_xep: "Sắp xếp câu",
  dien_chu: "Điền chữ",
  viet_mo: "Viết đoạn",
};

function Trend({ now, before }) {
  if (!before) return null;
  const a = before.tong ? before.dung / before.tong : 0;
  const b = now.tong ? now.dung / now.tong : 0;
  const cls = b > a + 0.001 ? "is-up" : b < a - 0.001 ? "is-down" : "";
  const arrow = cls === "is-up" ? "↑" : cls === "is-down" ? "↓" : "=";
  return (
    <span className={`rm-trend ${cls}`} title="So với lượt thi trước cùng cấp">
      Lần trước {before.dung}/{before.tong} {arrow}
    </span>
  );
}

function Bars({ groups }) {
  if (!groups?.length) return null;
  return (
    <ul className="rm-bars" aria-label="Tỷ lệ đúng theo kỹ năng và dạng câu">
      {groups.map((g) => {
        const pct = Math.round(g.ty_le * 100);
        return (
          <li key={`${g.ky_nang}-${g.dang}`} className={g.ty_le < 0.6 ? "is-weak" : ""}>
            <span className="rm-bars__name">
              {SKILL[g.ky_nang]} · {DANG[g.dang] || g.dang}
            </span>
            <span className="rm-bars__track" aria-hidden="true">
              <span style={{ width: `${pct}%` }} />
            </span>
            <span className="rm-bars__val">
              <b>{pct}%</b> <small>({g.dung}/{g.tong})</small>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default function RoadmapCard({ luotId, onJumpQuestion = null }) {
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
      .catch((err) =>
        alive && setState({ loading: false, data: null, error: err?.message || "Không tải được gợi ý lộ trình" })
      );
    return () => {
      alive = false;
    };
  }, [token, luotId]);

  function handleJump(no) {
    if (onJumpQuestion) {
      onJumpQuestion(no);
      return;
    }
    document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

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
    const tab = window.open("", "_blank");
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
        <div className="rm-head__text">
          <div className="rm-head__kicker">CHẨN ĐOÁN AI & KẾ HOẠCH CẢI THIỆN</div>
          <h2 id="rm-title">Xiang phân tích năng lực & gợi ý lộ trình ôn tập</h2>
          <p className="lv-help">
            Đánh giá độ vững theo từng dạng bài và ưu tiên các nhóm đạt dưới 60% cần khắc phục ngay.
            {data?.lan_truoc && <> So sánh với lần thi trước ({data.lan_truoc.ten_de}).</>}
          </p>
        </div>
      </header>

      {loading && <p className="lv-muted">Xiang đang tổng hợp chẩn đoán từ bài làm của bạn…</p>}
      {error && (
        <p role="alert" className="lv-alert">
          {error}
        </p>
      )}

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
                      <h3>
                        {SKILL[g.ky_nang]} · {DANG[g.dang] || g.dang}
                      </h3>
                      {g.phan_ten.length > 0 && <p>{g.phan_ten.join(" · ")}</p>}
                    </div>
                    <div className="rm-plan__score">
                      <b>
                        {g.dung}/{g.tong} câu
                      </b>
                      <Trend now={g} before={g.truoc} />
                    </div>
                  </div>

                  {g.ghi_chu_cap && (
                    <p className="rm-level">
                      <span>💡 {g.ghi_chu_cap}</span>
                      {g.mo_cap && (
                        <>
                          {" "}
                          <Link to={`/hoc-vien/on-luyen/${g.mo_cap.ky_nang}?cap=${g.mo_cap.cap_do_id}`}>
                            Mở cấp này →
                          </Link>
                        </>
                      )}
                    </p>
                  )}

                  <ol className="rm-steps">
                    {g.cau_sai.length > 0 && (
                      <li className="rm-step">
                        <div className="rm-step__body">
                          <p className="rm-step__why">
                            Đối chiếu lại <b>{g.cau_sai.length} câu chưa đạt</b> thuộc dạng này trong đề vừa thi
                          </p>
                          <div className="rm-chips">
                            {g.cau_sai.map((n) => (
                              <button
                                key={n}
                                type="button"
                                className="rm-chip"
                                onClick={() => handleJump(n)}
                                aria-label={`Đến câu ${n}`}
                              >
                                Câu {n}
                              </button>
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
                            {s.dich.loai === "bai" ? (
                              <>
                                Bài luyện tập đề xuất: <b>{s.dich.thua} · {s.dich.ten}</b>
                                {s.dich.cap ? ` (${s.dich.cap})` : ""}
                              </>
                            ) : (
                              <>
                                Tài liệu ôn tập: <b>{s.dich.ten}</b>
                              </>
                            )}
                          </p>
                        </div>
                        {s.dich.kha_dung ? (
                          s.dich.loai === "bai" ? (
                            <button
                              type="button"
                              className="xbtn xbtn--sm rm-step__go"
                              disabled={busy}
                              onClick={() => openLesson(s.dich.ma_goc_id)}
                            >
                              Luyện ngay →
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="xbtn xbtn--ghost xbtn--sm rm-step__go"
                              onClick={() => openMaterial(s.dich.id)}
                            >
                              Mở tài liệu
                            </button>
                          )
                        ) : (
                          <span className="rm-step__off">Đang cập nhật</span>
                        )}
                      </li>
                    ))}
                    {g.buoc.length === 0 && (
                      <li className="rm-step">
                        <p className="rm-step__why">
                          Hãy xem lời giải chi tiết từng câu bên dưới và đặt câu hỏi với Trợ giảng Xiang để củng cố dạng bài này.
                        </p>
                      </li>
                    )}
                    {g.hoc_them?.length > 0 && (
                      <li className="rm-step">
                        <div className="rm-step__body">
                          <p className="rm-step__name">Tài liệu tham khảo mở rộng</p>
                          <ul className="rm-links">
                            {g.hoc_them.map((x) => (
                              <li key={x.url}>
                                <a href={x.url} target="_blank" rel="noopener noreferrer">
                                  {x.ten} ↗
                                </a>
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
          {notice && (
            <p role="alert" className="lv-alert">
              {notice}
            </p>
          )}
          {data.goi_y.length > 0 && (
            <p className="lv-help rm-foot">
              Sau khi hoàn thành các bài luyện tập ưu tiên trên, hãy thử sức lại một đề mới — Xiang sẽ đối chiếu sự tiến bộ của từng nhóm kỹ năng so với lần này.
            </p>
          )}
        </>
      )}
    </section>
  );
}
