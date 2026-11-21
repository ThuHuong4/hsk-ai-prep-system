import { http } from "../../../shared/api/httpClient.js";

export const getNotebook = (token, trangThai, signal) =>
  http.get(`/api/so-tay${trangThai ? `?trang_thai=${trangThai}` : ""}`, { token, signal });
export const startNotebookReview = (token) => http.post("/api/so-tay/on", undefined, { token });
export const getNotebookReview = (token, id, signal) => http.get(`/api/so-tay/luot/${id}`, { token, signal });
export const checkNotebookAnswer = (token, id, body) => http.post(`/api/so-tay/luot/${id}/kiem-tra`, body, { token });
export const abandonNotebookReview = (token, id) => http.post(`/api/so-tay/luot/${id}/bo`, undefined, { token });
export const askNotebookXiang = (token, id, body) => http.post(`/api/so-tay/luot/${id}/hoi-xiang`, body, { token });
export const getMissions = (token, signal) => http.get("/api/nhiem-vu", { token, signal });
export const claimMission = (token, ma) => http.post(`/api/nhiem-vu/${ma}/nhan`, undefined, { token });
