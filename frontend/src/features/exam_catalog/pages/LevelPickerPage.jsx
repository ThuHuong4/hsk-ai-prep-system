import { Link } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import { getHskLevels } from "../api/getHskLevels.js";
import { parseLevelId } from "../utils/levels.js";

export default function LevelPickerPage({ title, description, basePath }) {
  const { data, error, loading } = useRequest((signal) => getHskLevels(signal), []);
  const levels = (data ?? []).filter((level) => parseLevelId(level.ma_cap_do));

  return (
    <section>
      <h1>{title}</h1>
      <p className="muted">{description}</p>
      {loading && <p className="muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && (
        <ul className="card-grid">
          {levels.map((level) => (
            <li key={level.ma_cap_do}>
              <Link className="card" to={`${basePath}/hsk/${level.ma_cap_do}`}>
                <span className="card__title">{level.ten_cap_do}</span>
                {level.mo_ta && <span className="muted">{level.mo_ta}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}