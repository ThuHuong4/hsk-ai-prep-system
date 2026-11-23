import { useEffect, useState } from "react";

// Giao diện sáng là mặc định; chỉ tối khi người dùng tự bấm nút. Lưu trong trình duyệt, áp lên <html data-theme>.
const KEY = "xianglingo-theme";
const EVENT = "xianglingo-theme-change";

export function readTheme() {
  try {
    if (localStorage.getItem(KEY) === "dark") return "dark";
  } catch { /* trình duyệt chặn lưu trữ: dùng mặc định */ }
  return "light";
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
}

export function setTheme(theme) {
  try { localStorage.setItem(KEY, theme); } catch { /* bỏ qua */ }
  applyTheme(theme);
  window.dispatchEvent(new CustomEvent(EVENT, { detail: theme }));
}

export function useTheme() {
  const [theme, set] = useState(readTheme);
  useEffect(() => {
    const on = (e) => set(e.detail);
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);
  return [theme, () => setTheme(theme === "dark" ? "light" : "dark")];
}
