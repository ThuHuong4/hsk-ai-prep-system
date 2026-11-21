import { Link, useParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { listPublishedExams } from "../../mock_test/api/mockTestApi.js";
import "../styles/catalog.css";
import { ZH_NUM, examSkills, levelClass, levelSkills } from "../utils/display.js";
import { parseLevelId } from "../utils/levels.js";

export default function ExamListPage({ basePath }) {
  const { maCapDo } = useParams();
  const level = parseLevelId(maCapDo);
  const { data, error, loading } = useRequest(
    level ? (signal) => listPublishedExams(level, signal) : null,
    [level]
  );
  const first = data?.[0];

  return (
    <section className="xc">
      <Link className="xc-back" to={basePath}><Icon name="arrowLeft" />Tất cả cấp</Link>
      {!level ? (
        <p role="alert">Cấp độ không hợp lệ.</p>
      ) : (
        <>
          <header className={`xc-title ${levelClass(level)}`}>
            <span className="xc-tile xc-tile--lg" aria-hidden="true">{ZH_NUM[level]}</span>
            <span>
              <h1>Đề thi thử HSK {level}</h1>
              <p>{first ? `Mỗi đề ${first.so_cau} câu · ${first.thoi_luong_phut} phút · ${examSkills(first)}` : levelSkills(level)}</p>
            </span>
          </header>
          {loading && <p className="xc-muted">Đang tải...</p>}
          {error && <p role="alert">{error}</p>}
          {data && data.length === 0 && (
            <div className="xc-empty">
              <p>Cấp này chưa có đề đã đăng.</p>
              <Link className="xc-btn xc-btn--plain xc-btn--sm" to={basePath}>Chọn cấp khác</Link>
            </div>
          )}
          {data && data.length > 0 && (
            <ul className="xc-list">
              {data.map((exam) => (
                <li key={exam.ma_goc_id} className="xc-exam">
                  <span className="xc-tag">HSK {level}</span>
                  <span className="xc-exam__body">
                    <span className="xc-exam__name">{exam.ten}</span>
                    <span className="xc-meta">
                      <span><Icon name="book" />{exam.so_cau} câu</span>
                      <span><Icon name="timer" />{exam.thoi_luong_phut} phút</span>
                      <span>Mã {exam.ma_de}</span>
                    </span>
                  </span>
                  <Link className="xc-btn xc-btn--plain xc-btn--sm" to={`${basePath}/de/${exam.ma_goc_id}`}>Xem</Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
