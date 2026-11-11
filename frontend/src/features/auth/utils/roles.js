// Khớp bảng vai_tro và app/security/roles.py
export const ROLE = Object.freeze({
  HOC_VIEN: 1,
  QUAN_TRI_VIEN: 2,
  GIANG_VIEN: 3,
});

const HOME_PATHS = {
  [ROLE.HOC_VIEN]: "/hoc-vien",
  [ROLE.QUAN_TRI_VIEN]: "/quan-tri",
  [ROLE.GIANG_VIEN]: "/giang-vien",
};

export function homePathForRole(role) {
  return HOME_PATHS[role] ?? null;
}