import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { listPublishedExams } from "../../mock_test/api/mockTestApi.js";
import { getHskLevels } from "../api/getHskLevels.js";
import "../styles/catalog.css";
import { ZH_NUM, examSkills, levelClass, levelSkills } from "../utils/display.js";
import { parseLevelId } from "../utils/levels.js";

// kind = "exam": kèm số đề đã đăng của từng cấp; "practice": chỉ chọn cấp rồi chọn kỹ năng
async function loadLevels(kind, signal) {
  const levels = (await getHskLevels(signal)).filter((l) => parseLevelId(l.ma_cap_do));
  if (kind !== "exam") return levels.map((l) => ({ ...l, exams: null }));
  const lists = await Promise.all(levels.map((l) => listPublishedExams(l.ma_cap_do, signal).catch(() => null)));
  return levels.map((l, i) => ({ ...l, exams: lists[i] }));
}

export default function LevelPickerPage({ title, description, basePath, kind = "exam" }) {
  const { data, error, loading } = useRequest((signal) => loadLevels(kind, signal), [kind]);
  const exam = kind === "exam";

  return (
    <section className="xc">
      <header className="xc-head xc-head--center">
        <span className="xc-eyebrow">{exam ? "Thi thử HSK" : "Ôn luyện"}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>
      {loading && <p className="xc-muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <ul className={`xc-levels${data.length >= 4 ? " xc-levels--4" : ""}`}>
          {data.map((level) => {
            const n = parseLevelId(level.ma_cap_do);
            const first = level.exams?.[0];
            return (
              <li key={level.ma_cap_do}>
                <Link className={`xc-level ${levelClass(n)}`} to={`${basePath}/hsk/${level.ma_cap_do}`}>
                  <span className="xc-level__top">
                    <span className="xc-tile" aria-hidden="true">{ZH_NUM[n]}</span>
                    <span className="xc-go" aria-hidden="true"><Icon name="arrow" /></span>
                  </span>
                  <h2>{level.ten_cap_do}</h2>
                  {first && <strong>{first.so_cau} câu · {first.thoi_luong_phut} phút</strong>}
                  <span className="xc-muted">{first ? examSkills(first) : levelSkills(n)}</span>
                  {exam ? (
                    <span className={`xc-level__foot${level.exams?.length ? "" : " is-empty"}`}>
                      {level.exams == null ? "Không tải được số đề" : level.exams.length ? `${level.exams.length} đề` : "Chưa có đề"}
                    </span>
                  ) : (
                    <span className="xc-level__foot">Chọn kỹ năng</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      {exam && (
        <p className="xc-note"><Icon name="info" />Bạn chọn được bất kỳ cấp HSK. Thi thử không phụ thuộc tiến độ Ôn luyện.</p>
      )}
    </section>
  );
}
