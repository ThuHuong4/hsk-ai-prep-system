// Các hàm định dạng và xử lý đường dẫn media dùng chung toàn ứng dụng Frontend.

export function mediaUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path) || path.startsWith("/")) return path;
  return `/media/${path}`;
}

export function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

// Tách chuỗi phương án dạng "商店 [shāngdiàn]" → { text: "商店", pinyin: "shāngdiàn" }
export function splitOption(value) {
  if (!value) return { text: "", pinyin: null };
  const m = value.match(/^(.*?)\s*\[([^\]]+)\]\s*$/);
  return m ? { text: m[1], pinyin: m[2] } : { text: value, pinyin: null };
}
