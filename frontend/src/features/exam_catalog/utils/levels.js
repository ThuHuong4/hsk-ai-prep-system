export const MIN_LEVEL = 1;
export const MAX_LEVEL = 4;

// Trả số cấp 1–4 nếu hợp lệ, ngược lại null
export function parseLevelId(value) {
  if (!/^\d+$/.test(String(value ?? ""))) return null;
  const level = Number(value);
  return level >= MIN_LEVEL && level <= MAX_LEVEL ? level : null;
}