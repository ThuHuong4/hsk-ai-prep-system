import { useEffect, useState } from "react";

import "../styles/practice.css";
import Icon from "../../../shared/components/Icon.jsx";
import { rankOf } from "../../../shared/rank.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import LevelUpDialog from "../../profile/components/LevelUpDialog.jsx";

// Bậc đã thấy lần trước (mỗi trình duyệt): lên bậc mới thì hiện hộp chúc mừng một lần
function seenRank(uid, value) {
  const key = `xianglingo-bac-${uid}`;
  try {
    if (value === undefined) {
      const v = Number(localStorage.getItem(key));
      return Number.isFinite(v) && v > 0 ? v : null;
    }
    localStorage.setItem(key, String(value));
  } catch {
    // trình duyệt chặn lưu trữ: bỏ qua hiệu ứng lên bậc
  }
  return null;
}

// Ô năng lượng và điểm KN trên thanh trên (chỉ hiện khi đã có dữ liệu thật)
export default function StudentStats({ stats, compact = false }) {
  const { user } = useAuth();
  const [levelUp, setLevelUp] = useState(null);
  const rank = stats?.kn != null ? rankOf(stats.kn) : null;
  const uid = user?.ma_nguoi_dung;

  useEffect(() => {
    if (!rank || !uid || compact) return;
    const before = seenRank(uid);
    if (before !== null && rank.bac > before) setLevelUp(rank);
    if (before === null || rank.bac > before) seenRank(uid, rank.bac);
  }, [rank?.bac, uid, compact]); // eslint-disable-line react-hooks/exhaustive-deps

  if (stats?.nang_luong == null) return null;
  return (
    <span className={`sp-stats${compact ? " sp-stats--compact" : ""}`}>
      {!compact && (
        <span className="sp-stat sp-stat--fire" title="Chuỗi ngày học liên tiếp">
          <Icon name="flame" size={18} /><b>{stats.chuoi_ngay ?? 0}</b><small>ngày liên tiếp</small>
        </span>
      )}
      <span className="sp-stat sp-stat--energy" title="Năng lượng">
        <Icon name="sprout" size={18} /><b>{stats.nang_luong}/{stats.nang_luong_toi_da}</b><small>năng lượng</small>
      </span>
      {!compact && (
        <span className="sp-stat sp-stat--kn"
          title={rank ? `${rank.ten}${rank.next ? ` · còn ${rank.con_thieu} KN để lên ${rank.next.ten}` : ""}` : "Điểm kinh nghiệm"}>
          <Icon name="bolt" size={18} /><b>{stats.kn}</b><small>{rank ? rank.ten : "điểm KN"}</small>
        </span>
      )}
      {levelUp && <LevelUpDialog rank={levelUp} onClose={() => setLevelUp(null)} />}
    </span>
  );
}
