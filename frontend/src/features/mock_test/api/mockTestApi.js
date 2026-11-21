import { http } from "../../../shared/api/httpClient.js";

export const listPublishedExams = (capDoId, signal) => http.get(`/api/thi-thu/de?cap_do_id=${encodeURIComponent(capDoId)}`, { signal });
export const getExamInfo = (maGoc, signal) => http.get(`/api/thi-thu/de/${maGoc}`, { signal });
export const startAttempt = (token, maGoc) => http.post(`/api/thi-thu/de/${maGoc}/bat-dau`, undefined, { token });
export const getAttempt = (token, id, signal) => http.get(`/api/thi-thu/luot/${id}`, { token, signal });
export const saveAnswer = (token, id, body) => http.put(`/api/thi-thu/luot/${id}/tra-loi`, body, { token });
export const submitAttempt = (token, id) => http.post(`/api/thi-thu/luot/${id}/nop`, undefined, { token });
export const getResult = (token, id, signal) => http.get(`/api/thi-thu/luot/${id}/ket-qua`, { token, signal });
export const getHistory = (token, signal) => http.get("/api/thi-thu/lich-su", { token, signal });
