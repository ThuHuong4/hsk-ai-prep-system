import { Link, useParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import { getExams } from "../api/getExams.js";
import { parseLevelId } from "../utils/levels.js";

export default function ExamListPage({ basePath }) {
  const { maCapDo } = useParams();
  const level = parseLevelId(maCapDo);
  const { data, error, loading } = useRequest(
    level ? (signal) => getExams(level, signal) : null,
    [level]
  );

  return (
    <section>
      <Link className="back-link" to={basePath}>← Chọn cấp khác</Link>
      {!level ? (
        <p role="alert">Cấp độ không hợp lệ.</p>
      ) : (
        <>
          <h1>Đề thi thử HSK {level}</h1>
          {loading && <p className="muted">Đang tải...</p>}
          {error && <p role="alert">{error}</p>}
          {data && data.length === 0 && <p className="muted">Cấp này chưa có đề đã xuất bản.</p>}
          {data && data.length > 0 && (
            <ul className="card-grid">
              {data.map((exam) => (
                <li key={exam.ma_bo_de}>
                  <Link className="card" to={`${basePath}/de/${exam.ma_bo_de}`}>
                    <span className="card__title">{exam.ten_bo_de}</span>
                    <span className="muted">{Math.round(exam.thoi_gian_giay / 60)} phút</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}