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
// Soạn câu với AI: AI soạn + tự soát lỗi; Giảng viên trao đổi, sửa và duyệt
// Chất lượng câu hỏi (dữ liệu làm bài thật) và kiểm tra trùng lặp
export const getItemQuality = (token, params, signal) => http.get(`/api/giang-vien/chat-luong-cau-hoi${query(params)}`, { token, signal });
export const checkSimilar = (token, body) => http.post("/api/giang-vien/cau-hoi-trung", body, { token });
// Trợ lý AI của Giảng viên (khung hỏi đáp ở mọi trang)
export const askLecturerAssistant = (token, body) => http.post("/api/giang-vien/tro-ly-ai", body, { token });
export const aiSuggestPlan = (token, body) => http.post("/api/giang-vien/cau-hoi/ai-goi-y", body, { token });
export const aiDraftQuestions = (token, body) => http.post("/api/giang-vien/cau-hoi/ai-soan-nhap", body, { token });
export const aiChatDraft = (token, body) => http.post("/api/giang-vien/cau-hoi/ai-trao-doi", body, { token });
export const aiReviewDrafts = (token, items) => http.post("/api/giang-vien/cau-hoi/ai-kiem-tra", { cau_hoi: items }, { token });
export const aiApproveDrafts = (token, items) => http.post("/api/giang-vien/cau-hoi/ai-duyet", { cau_hoi: items }, { token });
export const listKnowledgeGroups = (token, signal) => http.get("/api/giang-vien/nhom-kien-thuc", { token, signal });
export const updateQuestion = (token, id, body) => http.put(`/api/giang-vien/cau-hoi/${id}`, body, { token });
export const questionAction = (token, id, action) => http.post(`/api/giang-vien/cau-hoi/${id}/${action}`, undefined, { token });
export const deleteQuestion = (token, id) => http.delete(`/api/giang-vien/cau-hoi/${id}`, { token });

// Đề thi thử
export const listExams = (token, params, signal) => http.get(`/api/giang-vien/de-thi${query(params)}`, { token, signal });
export const getExam = (token, id, signal) => http.get(`/api/giang-vien/de-thi/${id}`, { token, signal });
export const createExam = (token, body) => http.post("/api/giang-vien/de-thi", body, { token });
export const updateExam = (token, id, body) => http.put(`/api/giang-vien/de-thi/${id}`, body, { token });
export const saveExamItems = (token, id, items) => http.put(`/api/giang-vien/de-thi/${id}/cau-hoi`, { cau_hoi: items }, { token });
export const buildExamListeningTape = (token, id) => http.post(`/api/giang-vien/de-thi/${id}/ghep-bang-nghe`, undefined, { token });
export const examAction = (token, id, action) => http.post(`/api/giang-vien/de-thi/${id}/${action}`, undefined, { token });
export const deleteExam = (token, id) => http.delete(`/api/giang-vien/de-thi/${id}`, { token });
// Ghép đề với AI: AI chọn câu đã duyệt; Giảng viên trao đổi, tạo đề nháp rồi tự Đăng
export const aiComposeExam = (token, body) => http.post("/api/giang-vien/de-thi/ai-ghep", body, { token });
export const aiCreateExam = (token, body) => http.post("/api/giang-vien/de-thi/ai-tao", body, { token });
// Soạn đề mới với AI theo từng phần HSK 2.0 (kèm tạo hình, giọng đọc)
export const getExamBlueprint = (token, capDoId, signal) =>
  http.get(`/api/giang-vien/de-thi/ai-cau-truc${query({ cap_do_id: capDoId })}`, { token, signal });
export const aiGeneratePart = (token, body) => http.post("/api/giang-vien/de-thi/ai-phan/soan", body, { token });
export const aiChatPart = (token, body) => http.post("/api/giang-vien/de-thi/ai-phan/trao-doi", body, { token });
export const aiApprovePart = (token, body) => http.post("/api/giang-vien/de-thi/ai-phan/duyet", body, { token });
export const aiMakeImage = (token, moTa) => http.post("/api/giang-vien/de-thi/ai-tep/hinh", { mo_ta: moTa }, { token });
// Tạo đề hoàn chỉnh với AI (chạy nền) và duyệt đề
const JOB = "/api/giang-vien/de-thi/ai-de";
export const listExamJobs = (token, signal) => http.get(JOB, { token, signal });
export const createExamJob = (token, body) => http.post(JOB, body, { token });
export const getExamJob = (token, id, signal) => http.get(`${JOB}/${id}`, { token, signal });
export const resumeExamJob = (token, id) => http.post(`${JOB}/${id}/chay-tiep`, undefined, { token });
export const deleteExamJob = (token, id) => http.delete(`${JOB}/${id}`, { token });
export const markJobItem = (token, id, key, dat) => http.post(`${JOB}/${id}/muc/${key}/dat`, { dat }, { token });
export const markJobGreen = (token, id, phan, tatCaHopLe = false) =>
  http.post(`${JOB}/${id}/dat-xanh`, { phan: phan ?? null, tat_ca_hop_le: tatCaHopLe }, { token });
export const fixJobItem = (token, id, key, tinNhan) => http.post(`${JOB}/${id}/muc/${key}/sua`, { tin_nhan: tinNhan }, { token });
export const redoJobItem = (token, id, key) => http.post(`${JOB}/${id}/muc/${key}/lam-lai`, undefined, { token });
export const jobItemFile = (token, id, key, path, duongDan = null) =>
  http.post(`${JOB}/${id}/muc/${key}/tep`, { path, duong_dan: duongDan }, { token });
export const assembleJobAudio = (token, id, nghi) => http.post(`${JOB}/${id}/ghep-am-thanh`, { nghi }, { token });
export const approveExamJob = (token, id, body) => http.post(`${JOB}/${id}/duyet`, body, { token });
export const aiMakeAudio = (token, capDoId, loiNghe) =>
  http.post("/api/giang-vien/de-thi/ai-tep/am-thanh", { cap_do_id: capDoId, loi_nghe: loiNghe }, { token });

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
