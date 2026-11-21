import { STATUS_LABELS, WORD_STATUS_LABELS } from "../utils/labels.js";

const CLASS = { xuat_ban: "da_dang", ngung_xuat_ban: "da_an" };

export default function StatusBadge({ status, label }) {
  const text = label ?? STATUS_LABELS[status] ?? WORD_STATUS_LABELS[status] ?? status;
  return <span className={`lv-status lv-status--${CLASS[status] ?? status}`}>{text}</span>;
}
