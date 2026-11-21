import { http } from "../../../shared/api/httpClient.js";

export const getPracticeOverview = (token, signal) => http.get("/api/on-luyen/tong-quan", { token, signal });
export const getSkillPath = (token, kyNang, capDoId, signal) =>
  http.get(`/api/on-luyen/lo-trinh?ky_nang=${kyNang}${capDoId ? `&cap_do_id=${capDoId}` : ""}`, { token, signal });
export const startLesson = (token, maGoc) => http.post(`/api/on-luyen/bai/${maGoc}/bat-dau`, undefined, { token });
export const getLessonAttempt = (token, id, signal) => http.get(`/api/on-luyen/luot/${id}`, { token, signal });
export const checkAnswer = (token, id, body) => http.post(`/api/on-luyen/luot/${id}/kiem-tra`, body, { token });
export const abandonAttempt = (token, id) => http.post(`/api/on-luyen/luot/${id}/bo`, undefined, { token });

// Vượt đến thửa (mục 4.2)
export const startSkip = (token, thuaMaGoc) => http.post(`/api/on-luyen/vuot/${thuaMaGoc}/bat-dau`, undefined, { token });
export const getSkip = (token, id, signal) => http.get(`/api/on-luyen/vuot/luot/${id}`, { token, signal });
export const saveSkipAnswer = (token, id, cauHoiId, body) => http.put(`/api/on-luyen/vuot/luot/${id}/cau/${cauHoiId}`, body, { token });
export const submitSkip = (token, id) => http.post(`/api/on-luyen/vuot/luot/${id}/nop`, undefined, { token });
export const abandonSkip = (token, id) => http.post(`/api/on-luyen/vuot/luot/${id}/bo`, undefined, { token });
export const askSkipXiang = (token, id, body) => http.post(`/api/on-luyen/vuot/luot/${id}/hoi-xiang`, body, { token });

// Bắt đầu cấp / Vượt chặng (mục 4.2): loai = "bat-dau-cap" | "vuot-chang"; lượt dùng chung API /vuot/luot/{id}
export const startLevelTest = (token, capDoId, kyNang, loai) =>
  http.post(`/api/on-luyen/cap/${capDoId}/${kyNang}/${loai}/bat-dau`, undefined, { token });
