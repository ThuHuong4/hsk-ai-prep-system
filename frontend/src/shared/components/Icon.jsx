// Biểu tượng nét đơn giản dùng chung (stroke theo màu chữ)
const PATHS = {
  home: "M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  doc: "M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM9 12h6M9 16h6",
  spark: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z",
  timer: "M12 8v5l3 2M9 2h6M12 22a8 8 0 1 0 0-16 8 8 0 0 0 0 16z",
  route: "M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 17h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7",
  check: "M4 12.5 9.5 18 20 6",
  alert: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 7v6M12 16.5v.5",
  logout: "M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 8l-4 4 4 4M6 12h10",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
  plus: "M12 5v14M5 12h14",
  user: "M20 21v-1.5A4.5 4.5 0 0 0 15.5 15h-7A4.5 4.5 0 0 0 4 19.5V21M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  book: "M4 19V5.5A2.5 2.5 0 0 1 6.5 3H20v14H6.5A2.5 2.5 0 0 0 4 19.5 2.5 2.5 0 0 0 6.5 22H20v-5",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  menu: "M4 6h16M4 12h16M4 18h16",
  audio: "M11 5 6 9H3v6h3l5 4zM15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13",
  image: "M4 4h16v16H4zM8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM20 15l-5-5L5 20",
  layers: "M12 3 2 8l10 5 10-5zM2 13l10 5 10-5",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 11v6M12 7.5v.5",
  back: "M15 18l-6-6 6-6",
  arrow: "M5 12h14M13 6l6 6-6 6",
  sprout: "M12 21v-9M12 12c0-4 3-7 8-7 0 5-3 7-8 7zM12 14c0-3-2-6-7-6 0 4 3 6 7 6z",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7z",
  lock: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
  play: "M7 4v16l13-8z",
  replay: "M3 12a9 9 0 1 0 3-6.7M3 4v5h5",
  arrowLeft: "M19 12H5M11 6l-6 6 6 6",
  chart: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  upload: "M12 15V3M7 8l5-5 5 5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  flame: "M12 22a7 7 0 0 0 7-7c0-4-3-6-4-9-1 2-2 3-4 3 0-2-1-4-3-6-1 4-3 7-3 12a7 7 0 0 0 7 7z",
  up: "M12 19V5M5 12l7-7 7 7",
  down: "M12 5v14M19 12l-7 7-7-7",
  x: "M6 6l12 12M18 6 6 18",
  pen: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
};

export default function Icon({ name, size = 20, className = "" }) {
  return (
    <svg className={`ico ${className}`} width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"
      fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={PATHS[name]} />
    </svg>
  );
}
