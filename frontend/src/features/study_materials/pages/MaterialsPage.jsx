import { useEffect, useMemo, useState } from "react";

import Icon from "../../../shared/components/Icon.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { fetchMaterialUrl, listExternal, listMaterials } from "../api/materialsApi.js";
import "../styles/materials.css";

// Mục 6.5: Học viên xem tài liệu đã đăng, lọc theo cấp/kỹ năng, mở PDF/ảnh trong khung, nghe audio bằng trình phát.
// Xem tài liệu không hoàn thành bài, không cộng KN, không tính nhiệm vụ.
const SKILLS = [
  ["nghe", "Nghe", "听"],
  ["doc", "Đọc", "读"],
  ["viet", "Viết", "写"],
  ["tu_vung", "Từ vựng", "词"],
];
const SKILL_VI = Object.fromEntries(SKILLS.map(([k, v]) => [k, v]));
const SKILL_HZ = Object.fromEntries(SKILLS.map(([k, , hz]) => [k, hz]));
const KIND = { pdf: "PDF", png: "Ảnh", jpg: "Ảnh", mp3: "Âm thanh", wav: "Âm thanh" };
const ICON = {
  PDF: "M7 3h7l5 5v13H7zM14 3v5h5M9.5 13h5M9.5 16.5h5",
  "Ảnh": "M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M15 9.5h.01",
  "Âm thanh": "M9 18V6l10-2v12M9 18a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0zM19 16a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z",
};
const size = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
const fold = (s) =>
  (s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase();

function Viewer({ item, token, onClose }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    let made = null;
    fetchMaterialUrl(token, item.id)
      .then((u) => {
        made = u;
        if (alive) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch((e) => alive && setError(e.message || "Không mở được tài liệu"));
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      alive = false;
      window.removeEventListener("keydown", onKey);
      if (made) URL.revokeObjectURL(made);
    };
  }, [item.id, token, onClose]);

  const kind = KIND[item.loai_tep];

  return (
    <div
      className="tl-view"
      role="dialog"
      aria-modal="true"
      aria-label={item.ten}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={`tl-view__box tl-view__box--${item.loai_tep === "pdf" ? "doc" : kind === "Ảnh" ? "img" : "audio"}`}>
        <header className="tl-view__head">
          <div className="tl-view__title">
            <strong>{item.ten}</strong>
            <small>
              {item.ten_cap_do || "Chung"}
              {item.ky_nang ? ` · ${SKILL_VI[item.ky_nang]}` : ""} · {kind} ({size(item.kich_thuoc)})
              {item.nguon ? ` · Nguồn: ${item.nguon}` : ""}
            </small>
          </div>
          {url && (
            <a className="xc-btn xc-btn--plain xc-btn--sm" href={url} download={`${item.ten}.${item.loai_tep}`}>
              Tải về
            </a>
          )}
          {url && (
            <a className="xc-btn xc-btn--plain xc-btn--sm" href={url} target="_blank" rel="noreferrer">
              Mở tab mới
            </a>
          )}
          <button type="button" className="tl-view__close" onClick={onClose} aria-label="Đóng">
            ✕
          </button>
        </header>
        <div className="tl-view__body">
          {error && <p role="alert">{error}</p>}
          {!url && !error && <p className="xc-muted">Đang mở tài liệu...</p>}
          {url && item.loai_tep === "pdf" && <iframe title={item.ten} src={url} />}
          {url && kind === "Ảnh" && <img src={url} alt={item.ten} />}
          {url && kind === "Âm thanh" && <audio src={url} controls autoPlay />}
        </div>
      </div>
    </div>
  );
}

export default function MaterialsPage() {
  const { token } = useAuth();
  const { data, error, loading } = useRequest((signal) => listMaterials(token, signal), [token]);
  const [cap, setCap] = useState("");
  const [skill, setSkill] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(null);
  const links = useRequest((signal) => listExternal(token, signal), [token]);

  const items = data || [];
  const levels = useMemo(() => {
    const seen = new Map();
    items.forEach((t) => t.cap_do_id && seen.set(t.cap_do_id, t.ten_cap_do));
    return [...seen];
  }, [items]);

  const shown = items.filter(
    (t) =>
      (!cap || String(t.cap_do_id ?? "chung") === cap) &&
      (!skill || (t.ky_nang ?? "chung") === skill) &&
      (!q.trim() || fold(`${t.ten} ${t.mo_ta} ${t.nguon}`).includes(fold(q.trim())))
  );
  const hasGeneral = items.some((t) => !t.cap_do_id);
  const capName = cap && cap !== "chung" ? (levels.find(([id]) => String(id) === cap)?.[1] || "").replace(/\s/g, "") : "";
  const shownLinks = (links.data || []).filter(
    (x) => (!capName || x.cap.includes(capName)) && (!skill || x.ky_nang.includes(skill))
  );
  const hasFilter = Boolean(cap || skill || q.trim());

  function resetFilters() {
    setCap("");
    setSkill("");
    setQ("");
  }

  return (
    <section className="xc tl">
      <header className="xc-head">
        <span className="xc-eyebrow">Thư viện học liệu HSK 1–4</span>
        <h1>Tài liệu ôn tập</h1>
        <p>Tổng hợp sổ tay từ vựng, cẩm nang ngữ pháp, mẹo làm bài Nghe – Đọc – Viết xem trực tiếp ngay trên web.</p>
      </header>

      {error && <p role="alert">{error}</p>}
      {loading && <p className="xc-muted">Đang tải thư viện tài liệu...</p>}
      {data && !items.length && (
        <div className="xc-empty">
          <p>Hiện chưa có tài liệu nào được xuất bản.</p>
        </div>
      )}

      {items.length > 0 && (
        <>
          <div className="tl-toolbar">
            <div className="tl-toolbar__search">
              <div className="tl-search-wrap">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-3.5-3.5" />
                </svg>
                <input
                  className="tl-search"
                  type="search"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Tìm sổ tay từ vựng, ngữ pháp, mẹo làm bài..."
                  aria-label="Tìm tài liệu"
                />
                {q && (
                  <button type="button" className="tl-search__clear" onClick={() => setQ("")} aria-label="Xóa từ khóa">
                    ✕
                  </button>
                )}
              </div>

              <div className="tl-toolbar__count">
                <span>
                  Hiển thị <b>{shown.length}</b>/{items.length} tài liệu
                </span>
                {hasFilter && (
                  <button type="button" className="tl-reset" onClick={resetFilters}>
                    Đặt lại bộ lọc
                  </button>
                )}
              </div>
            </div>

            <div className="tl-toolbar__groups">
              <div className="tl-filter-group">
                <span className="tl-filter-label">Cấp độ</span>
                <div className="tl-chips" role="group" aria-label="Lọc theo cấp">
                  <button type="button" className={!cap ? "is-on" : ""} onClick={() => setCap("")}>
                    Mọi cấp
                  </button>
                  {levels.map(([id, name]) => (
                    <button key={id} type="button" className={cap === String(id) ? "is-on" : ""} onClick={() => setCap(String(id))}>
                      {name}
                    </button>
                  ))}
                  {hasGeneral && (
                    <button type="button" className={cap === "chung" ? "is-on" : ""} onClick={() => setCap("chung")}>
                      Chung
                    </button>
                  )}
                </div>
              </div>

              <div className="tl-filter-group">
                <span className="tl-filter-label">Kỹ năng</span>
                <div className="tl-chips" role="group" aria-label="Lọc theo kỹ năng">
                  <button type="button" className={!skill ? "is-on" : ""} onClick={() => setSkill("")}>
                    Mọi kỹ năng
                  </button>
                  {SKILLS.map(([k, v]) => (
                    <button key={k} type="button" className={skill === k ? "is-on" : ""} onClick={() => setSkill(k)}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {!shown.length ? (
            <div className="tl-empty">
              <p>Không tìm thấy tài liệu nào khớp với bộ lọc hiện tại.</p>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={resetFilters}>
                Xem toàn bộ tài liệu
              </button>
            </div>
          ) : (
            <ul className="tl-grid">
              {shown.map((t) => {
                const kind = KIND[t.loai_tep];
                const skSlug = (t.ky_nang || "chung").replace("_", "-");
                return (
                  <li key={t.id} className={`tl-card sk-${skSlug}`} onClick={() => setOpen(t)}>
                    <div className="tl-card__top">
                      <span className="tl-ico" aria-hidden="true">
                        {t.ky_nang && SKILL_HZ[t.ky_nang] ? (
                          <b className="hz">{SKILL_HZ[t.ky_nang]}</b>
                        ) : (
                          <svg viewBox="0 0 24 24">
                            <path d={ICON[kind]} />
                          </svg>
                        )}
                      </span>
                      <div className="tl-card__tags">
                        <span className="tl-badge tl-badge--level">{t.ten_cap_do || "Chung"}</span>
                        {t.ky_nang && <span className={`tl-badge tl-badge--${t.ky_nang}`}>{SKILL_VI[t.ky_nang]}</span>}
                      </div>
                    </div>

                    <h2 className="tl-card__title">{t.ten}</h2>
                    {t.mo_ta && <p className="tl-card__desc">{t.mo_ta}</p>}

                    {t.nguon && (
                      <p className="tl-card__source" title={t.nguon}>
                        Nguồn: {t.nguon}
                      </p>
                    )}

                    <div className="tl-card__foot">
                      <span className="tl-file-pill">
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d={ICON[kind]} />
                        </svg>
                        {kind} · {size(t.kich_thuoc)}
                      </span>
                      <button
                        type="button"
                        className="xc-btn xc-btn--sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpen(t);
                        }}
                      >
                        {kind === "Âm thanh" ? "Nghe ngay" : "Mở xem"} <Icon name="arrow" size={15} />
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}

      {shownLinks.length > 0 && (
        <div className="tl-links">
          <div className="tl-links__head">
            <span className="xc-eyebrow">Tài nguyên mở rộng</span>
            <h2>Học thêm từ nguồn bên ngoài</h2>
          </div>
          <ul>
            {shownLinks.map((x) => (
              <li key={x.url}>
                <a href={x.url} target="_blank" rel="noopener noreferrer">
                  <strong>{x.ten}</strong>
                  <span>{x.mo_ta}</span>
                  <small>{x.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]} ↗</small>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {open && <Viewer item={open} token={token} onClose={() => setOpen(null)} />}
    </section>
  );
}
