import { http } from "../../../shared/api/httpClient.js";

const qs = (params) => {
  const s = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null)).toString();
  return s ? `?${s}` : "";
};

export const getAdminOverview = (token, signal) => http.get("/api/quan-tri/tong-quan", { token, signal });
export const listAccounts = (token, params, signal) => http.get(`/api/quan-tri/tai-khoan${qs(params)}`, { token, signal });
export const lockAccount = (token, id, lyDo) => http.post(`/api/quan-tri/tai-khoan/${id}/khoa`, { ly_do: lyDo || null }, { token });
export const unlockAccount = (token, id, lyDo) => http.post(`/api/quan-tri/tai-khoan/${id}/mo-khoa`, { ly_do: lyDo || null }, { token });
export const changeRole = (token, id, vaiTroId, lyDo) => http.post(`/api/quan-tri/tai-khoan/${id}/vai-tro`, { vai_tro_id: vaiTroId, ly_do: lyDo || null }, { token });
export const listAdminLogs = (token, params, signal) => http.get(`/api/quan-tri/nhat-ky${qs(params)}`, { token, signal });
export const getAccount = (token, id, signal) => http.get(`/api/quan-tri/tai-khoan/${id}`, { token, signal });
export const createLecturer = (token, body) => http.post("/api/quan-tri/giang-vien", body, { token });
export const resendInvite = (token, id) => http.post(`/api/quan-tri/tai-khoan/${id}/gui-lai-email`, undefined, { token });
export const listRoles = (token, signal) => http.get("/api/quan-tri/vai-tro", { token, signal });
export const renameRole = (token, id, ten) => http.put(`/api/quan-tri/vai-tro/${id}`, { ten }, { token });
