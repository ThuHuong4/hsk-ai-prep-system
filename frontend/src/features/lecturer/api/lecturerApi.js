import { HttpError, http } from "../../../shared/api/httpClient.js";

function query(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "" && value !== false) search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

// Câu hỏi
export const listQuestions = (token, params, signal) =>
  http.get(`/api/giang-vien/cau-hoi${query(params)}`, { token, signal });
export const getQuestion = (token, id, signal) => http.get(`/api/giang-vien/cau-hoi/${id}`, { token, signal });
export const createQuestion = (token, body) => http.post("/api/giang-vien/cau-hoi", body, { token });
export const updateQuestion = (token, id, body) => http.put(`/api/giang-vien/cau-hoi/${id}`, body, { token });
export const questionAction = (token, id, action) => http.post(`/api/giang-vien/cau-hoi/${id}/${action}`, undefined, { token });
export const deleteQuestion = (token, id) => http.delete(`/api/giang-vien/cau-hoi/${id}`, { token });

// Đề thi thử
export const listExams = (token, params, signal) => http.get(`/api/giang-vien/de-thi${query(params)}`, { token, signal });
export const getExam = (token, id, signal) => http.get(`/api/giang-vien/de-thi/${id}`, { token, signal });
export const createExam = (token, body) => http.post("/api/giang-vien/de-thi", body, { token });
export const updateExam = (token, id, body) => http.put(`/api/giang-vien/de-thi/${id}`, body, { token });
export const saveExamItems = (token, id, items) => http.put(`/api/giang-vien/de-thi/${id}/cau-hoi`, { cau_hoi: items }, { token });
export const examAction = (token, id, action) => http.post(`/api/giang-vien/de-thi/${id}/${action}`, undefined, { token });
export const deleteExam = (token, id) => http.delete(`/api/giang-vien/de-thi/${id}`, { token });

// Tải tệp: gửi nội dung thô (không multipart); trả { duong_dan }
export async function uploadMedia(token, kind, file) {
  let response;
  try {
    response = await fetch(`/api/giang-vien/tep${query({ loai: kind, ten: file.name })}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
  } catch {
    throw new HttpError(0, "Không kết nối được máy chủ");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new HttpError(response.status, typeof detail === "string" ? detail : "Tải tệp thất bại", data);
  }
  return data;
}

// Tổng quan
export const getOverview = (token, signal) => http.get("/api/giang-vien/tong-quan", { token, signal });

// Cấp độ
export const listLevelsAdmin = (token, signal) => http.get("/api/giang-vien/cap-do", { token, signal });
export const createLevel = (token, body) => http.post("/api/giang-vien/cap-do", body, { token });
export const updateLevel = (token, id, body) => http.put(`/api/giang-vien/cap-do/${id}`, body, { token });
export const levelAction = (token, id, action) => http.post(`/api/giang-vien/cap-do/${id}/${action}`, undefined, { token });
export const deleteLevel = (token, id) => http.delete(`/api/giang-vien/cap-do/${id}`, { token });

// Từ vựng
export const listWords = (token, params, signal) => http.get(`/api/giang-vien/tu-vung${query(params)}`, { token, signal });
export const createWord = (token, body) => http.post("/api/giang-vien/tu-vung", body, { token });
export const updateWord = (token, id, body) => http.put(`/api/giang-vien/tu-vung/${id}`, body, { token });
export const importWords = (token, words) => http.post("/api/giang-vien/tu-vung/nhap-hang-loat", { tu: words }, { token });
export const wordAction = (token, id, action) => http.post(`/api/giang-vien/tu-vung/${id}/${action}`, undefined, { token });
export const deleteWord = (token, id) => http.delete(`/api/giang-vien/tu-vung/${id}`, { token });

// Tài liệu
export const listMaterials = (token, params, signal) => http.get(`/api/giang-vien/tai-lieu${query(params)}`, { token, signal });
export const getMaterial = (token, id, signal) => http.get(`/api/giang-vien/tai-lieu/${id}`, { token, signal });
export const createMaterial = (token, body) => http.post("/api/giang-vien/tai-lieu", body, { token });
export const updateMaterial = (token, id, body) => http.put(`/api/giang-vien/tai-lieu/${id}`, body, { token });
export const materialAction = (token, id, action) => http.post(`/api/giang-vien/tai-lieu/${id}/${action}`, undefined, { token });
export const deleteMaterial = (token, id) => http.delete(`/api/giang-vien/tai-lieu/${id}`, { token });

async function rawUpload(url, token, file) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
  } catch {
    throw new HttpError(0, "Không kết nối được máy chủ");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new HttpError(response.status, typeof detail === "string" ? detail : "Tải tệp thất bại", data);
  }
  return data;
}
export const uploadMaterialFile = (token, file) => rawUpload(`/api/giang-vien/tai-lieu/tep${query({ ten: file.name })}`, token, file);

// Tệp tài liệu cần đăng nhập: tải về dạng blob rồi tạo URL tạm để xem
export async function fetchMaterialBlobUrl(token, id) {
  let response;
  try {
    response = await fetch(`/api/giang-vien/tai-lieu/${id}/tep`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new HttpError(0, "Không kết nối được máy chủ");
  }
  if (!response.ok) throw new HttpError(response.status, "Không mở được tệp");
  return URL.createObjectURL(await response.blob());
}

// Lộ trình Ôn luyện
export const getPath = (token, params, signal) => http.get(`/api/giang-vien/lo-trinh${query(params)}`, { token, signal });
export const createLand = (token, body) => http.post("/api/giang-vien/thua", body, { token });
export const updateLand = (token, id, body) => http.put(`/api/giang-vien/thua/${id}`, body, { token });
export const moveLand = (token, id, huong) => http.post(`/api/giang-vien/thua/${id}/vi-tri${query({ huong })}`, undefined, { token });
export const landAction = (token, id, action) => http.post(`/api/giang-vien/thua/${id}/${action}`, undefined, { token });
export const deleteLand = (token, id) => http.delete(`/api/giang-vien/thua/${id}`, { token });
export const createLesson = (token, body) => http.post("/api/giang-vien/bai-on", body, { token });
export const getLesson = (token, id, signal) => http.get(`/api/giang-vien/bai-on/${id}`, { token, signal });
export const updateLesson = (token, id, body) => http.put(`/api/giang-vien/bai-on/${id}`, body, { token });
export const saveLessonItems = (token, id, items) => http.put(`/api/giang-vien/bai-on/${id}/cau-hoi`, { cau_hoi: items }, { token });
export const lessonAction = (token, id, action) => http.post(`/api/giang-vien/bai-on/${id}/${action}`, undefined, { token });
export const deleteLesson = (token, id) => http.delete(`/api/giang-vien/bai-on/${id}`, { token });

// Chấm Viết
export const listWriting = (token, params, signal) => http.get(`/api/giang-vien/cham-viet${query(params)}`, { token, signal });
export const getWriting = (token, id, signal) => http.get(`/api/giang-vien/cham-viet/${id}`, { token, signal });
export const claimWriting = (token, id) => http.post(`/api/giang-vien/cham-viet/${id}/nhan`, undefined, { token });
export const decideWriting = (token, id, body) => http.post(`/api/giang-vien/cham-viet/${id}/quyet-dinh`, body, { token });

// Báo lỗi nội dung
export const listReports = (token, params, signal) => http.get(`/api/giang-vien/bao-loi${query(params)}`, { token, signal });
export const claimReport = (token, id) => http.post(`/api/giang-vien/bao-loi/${id}/nhan`, undefined, { token });
export const resolveReport = (token, id, body) => http.post(`/api/giang-vien/bao-loi/${id}/xu-ly`, body, { token });
