import axios from 'axios';
import * as FileSystem from 'expo-file-system/legacy';
import { API_URL } from '@/lib/config';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000, // 15s - fail fast if backend unreachable
});

let currentAuthToken: string | null = null;

export function setAuthHeader(accessToken: string) {
  api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
  currentAuthToken = accessToken;
}

export function clearAuthHeader() {
  delete api.defaults.headers.common['Authorization'];
  currentAuthToken = null;
}

export function getAuthToken(): string | null {
  return currentAuthToken;
}

// Auth
export async function login(email: string, password: string) {
  const { data } = await api.post('/login', { email, password });
  return data;
}

export async function register(email: string, password: string, full_name: string, role: string) {
  const { data } = await api.post('/register', { email, password, full_name, role });
  return data;
}

// AI Pipeline (no auth required)
export async function extractText(file: { uri: string; name: string; type?: string }) {
  const formData = new FormData();
  formData.append('file', file as any);
  const { data } = await api.post('/extract-text', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.extracted_text;
}

export async function generateQuiz(text: string) {
  const { data } = await api.post('/generate-quiz', { text });
  return data.quiz;
}

export async function generateSummary(text: string) {
  const { data } = await api.post('/generate-summary', { text });
  return data.summary;
}

export async function generateFlashcards(text: string) {
  const { data } = await api.post('/generate-flashcards', { text });
  return data.flashcards;
}

// Classrooms
export async function createClassroom(name: string, subjectName?: string) {
  const { data } = await api.post('/classrooms', { name, subject_name: subjectName });
  return data;
}

export async function listClassrooms() {
  const { data } = await api.get('/classrooms');
  return data;
}

export async function getClassroom(id: number) {
  const { data } = await api.get(`/classrooms/${id}`);
  return data;
}

export async function joinClassroom(code: string) {
  const { data } = await api.post('/classrooms/join', { code: code.toUpperCase() });
  return data;
}

// Materials
export async function createMaterial(payload: {
  title: string;
  summary?: string;
  flashcards_json?: string;
  quiz_json?: string;
  classroom_id?: number;
  raw_text?: string;
}) {
  const { data } = await api.post('/materials', payload);
  return data;
}

/** Upload file, run OCR+AI, create material in one call (longer timeout for AI processing) */
export async function uploadMaterial(
  file: { uri: string; name: string; type?: string },
  title?: string,
  classroomId?: number
) {
  const formData = new FormData();
  formData.append('file', file as any);
  if (title) formData.append('title', title);
  if (classroomId) formData.append('classroom_id', String(classroomId));
  const { data } = await api.post('/upload-material', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 2 minutes for OCR only (AI generation is on-demand now)
  });
  return data;
}

/** Generate summary for material on-demand */
export async function generateMaterialSummary(id: number) {
  const { data } = await api.post(`/materials/${id}/generate-summary`, {}, { timeout: 120000 });
  return data;
}

/** Generate flashcards for material on-demand */
export async function generateMaterialFlashcards(id: number) {
  const { data } = await api.post(`/materials/${id}/generate-flashcards`, {}, { timeout: 120000 });
  return data;
}

/** Generate quiz for material on-demand */
export async function generateMaterialQuiz(id: number) {
  const { data } = await api.post(`/materials/${id}/generate-quiz`, {}, { timeout: 120000 });
  return data;
}

export async function listMaterials(classroom_id?: number) {
  const url = classroom_id ? `/materials?classroom_id=${classroom_id}` : '/materials';
  const { data } = await api.get(url);
  return data;
}

export async function getMaterial(id: number) {
  const { data } = await api.get(`/materials/${id}`);
  return data;
}

// Assignments
export async function createAssignment(payload: {
  title: string;
  quiz_json: string;
  classroom_id: number;
  material_id?: number;
}) {
  const { data } = await api.post('/assignments', payload);
  return data;
}

export async function listAssignments(classroom_id?: number) {
  const url = classroom_id ? `/assignments?classroom_id=${classroom_id}` : '/assignments';
  const { data } = await api.get(url);
  return data;
}

export async function getAssignment(id: number) {
  const { data } = await api.get(`/assignments/${id}`);
  return data;
}

export async function submitQuiz(assignment_id: number, answers: { question_index: number; selected_answer_index: number }[]) {
  const { data } = await api.post(`/assignments/${assignment_id}/submit`, { assignment_id, answers });
  return data;
}

// Progress (Teacher)
export async function getClassroomProgress(classroom_id: number) {
  const { data } = await api.get(`/progress/classroom/${classroom_id}`);
  return data;
}

/** Per-student DSP metrics (ZCR, energy, reading_ratio) for ECE demo */
export async function getClassroomDspMetrics(classroom_id: number) {
  const { data } = await api.get(`/progress/classroom/${classroom_id}/dsp-metrics`);
  return data;
}

export async function getAssignmentSubmissions(assignment_id: number) {
  const { data } = await api.get(`/progress/submissions/${assignment_id}`);
  return data;
}

/** Light health check to detect backend unreachable vs auth failure */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const { status } = await api.get('/', { timeout: 5000 });
    return status === 200;
  } catch {
    return false;
  }
}

// Analytics
export async function submitAnalytics(materialId: number, scrollSignal: number[]) {
  const { data } = await api.post('/submit-analytics', {
    material_id: materialId,
    scroll_signal: scrollSignal,
  });
  return data;
}

export async function getTeacherDashboardStats() {
  const { data } = await api.get('/teacher/dashboard-stats');
  return data;
}

/** Convert ArrayBuffer to base64 (chunked for large files). */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const chunk = 8192;
  let binary = '';
  for (let i = 0; i < bytes.length; i += chunk) {
    const sub = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode.apply(null, [...sub]);
  }
  return btoa(binary);
}

/**
 * Download a material file with authentication (axios + base64 for reliable auth headers).
 * Returns the local file URI after downloading to cache.
 */
export async function downloadMaterialFile(materialId: number, fileExt: string): Promise<string> {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  const remoteUrl = `${API_URL}/materials/${materialId}/file`;
  const localUri = `${FileSystem.cacheDirectory}material_${materialId}${fileExt}`;

  const fileInfo = await FileSystem.getInfoAsync(localUri);
  if (fileInfo.exists) {
    return localUri;
  }

  const { data } = await api.get<ArrayBuffer>(remoteUrl, {
    responseType: 'arraybuffer',
    timeout: 60000,
  });

  const base64 = arrayBufferToBase64(data);
  await FileSystem.writeAsStringAsync(localUri, base64, {
    encoding: FileSystem.EncodingType.Base64,
  });

  return localUri;
}
