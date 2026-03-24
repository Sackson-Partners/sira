import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('aip_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('aip_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  b2cLogin: (b2c_token: string) => api.post('/auth/b2c-login', { b2c_token }),
  register: (data: any) => api.post('/auth/register', data),
  refresh: (refresh_token: string) => api.post('/auth/refresh', { refresh_token }),
  me: () => api.get('/auth/me'),
  changePassword: (data: any) => api.post('/auth/change-password', data),
};

// ── Projects ────────────────────────────────────────────────────────────
export const projectsApi = {
  list: (params?: any) => api.get('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects', data),
  update: (id: number, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  stats: () => api.get('/projects/stats'),
  uploadExcel: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/projects/upload-excel', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  uploadDocument: (id: number, file: File, category = 'general') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('doc_category', category);
    return api.post(`/projects/${id}/documents`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  listDocuments: (id: number) => api.get(`/projects/${id}/documents`),
  deleteDocument: (projectId: number, docId: number) => api.delete(`/projects/${projectId}/documents/${docId}`),
  addNote: (id: number, content: string, note_type = 'general') => api.post(`/projects/${id}/notes`, { content, note_type }),
  listNotes: (id: number) => api.get(`/projects/${id}/notes`),
};

// ── Pipeline ────────────────────────────────────────────────────────────
export const pipelineApi = {
  list: (params?: any) => api.get('/pipeline', { params }),
  get: (id: number) => api.get(`/pipeline/${id}`),
  create: (data: any) => api.post('/pipeline', data),
  update: (id: number, data: any) => api.put(`/pipeline/${id}`, data),
  moveStage: (id: number, stage: string, probability?: number) =>
    api.patch(`/pipeline/${id}/stage`, { stage, probability }),
  delete: (id: number) => api.delete(`/pipeline/${id}`),
  stats: () => api.get('/pipeline/stats'),
};

// ── IC ──────────────────────────────────────────────────────────────────
export const icApi = {
  list: (params?: any) => api.get('/ic', { params }),
  get: (id: number) => api.get(`/ic/${id}`),
  create: (data: any) => api.post('/ic', data),
  update: (id: number, data: any) => api.put(`/ic/${id}`, data),
  delete: (id: number) => api.delete(`/ic/${id}`),
  castVote: (id: number, data: any) => api.post(`/ic/${id}/vote`, data),
  getVotes: (id: number) => api.get(`/ic/${id}/votes`),
  finalize: (id: number) => api.post(`/ic/${id}/finalize`),
};

// ── Investors ───────────────────────────────────────────────────────────
export const investorsApi = {
  list: (params?: any) => api.get('/investors', { params }),
  get: (id: number) => api.get(`/investors/${id}`),
  create: (data: any) => api.post('/investors', data),
  update: (id: number, data: any) => api.put(`/investors/${id}`, data),
  delete: (id: number) => api.delete(`/investors/${id}`),
  stats: () => api.get('/investors/stats'),
};

// ── Verifications ───────────────────────────────────────────────────────
export const verificationsApi = {
  list: (params?: any) => api.get('/verifications', { params }),
  get: (id: number) => api.get(`/verifications/${id}`),
  create: (data: any) => api.post('/verifications', data),
  uploadDocument: (id: number, file: File, doc_type = 'identity') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('doc_type', doc_type);
    return api.post(`/verifications/${id}/documents`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  review: (id: number, data: any) => api.post(`/verifications/${id}/review`, data),
};

// ── Data Rooms ──────────────────────────────────────────────────────────
export const dataRoomsApi = {
  list: (params?: any) => api.get('/data-rooms', { params }),
  get: (id: number) => api.get(`/data-rooms/${id}`),
  create: (data: any) => api.post('/data-rooms', data),
  update: (id: number, data: any) => api.put(`/data-rooms/${id}`, data),
  delete: (id: number) => api.delete(`/data-rooms/${id}`),
  uploadDocument: (id: number, file: File, folder_path = '/') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('folder_path', folder_path);
    return api.post(`/data-rooms/${id}/documents`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  listDocuments: (id: number, folder?: string) => api.get(`/data-rooms/${id}/documents`, { params: { folder_path: folder } }),
  grantAccess: (id: number, data: any) => api.post(`/data-rooms/${id}/access`, data),
  listAccess: (id: number) => api.get(`/data-rooms/${id}/access`),
  revokeAccess: (roomId: number, accessId: number) => api.delete(`/data-rooms/${roomId}/access/${accessId}`),
};

// ── Deal Rooms ──────────────────────────────────────────────────────────
export const dealRoomsApi = {
  list: (params?: any) => api.get('/deal-rooms', { params }),
  get: (id: number) => api.get(`/deal-rooms/${id}`),
  create: (data: any) => api.post('/deal-rooms', data),
  update: (id: number, data: any) => api.put(`/deal-rooms/${id}`, data),
  delete: (id: number) => api.delete(`/deal-rooms/${id}`),
  getMessages: (id: number) => api.get(`/deal-rooms/${id}/messages`),
  sendMessage: (id: number, content: string) => api.post(`/deal-rooms/${id}/messages`, { content }),
};

// ── Analytics ───────────────────────────────────────────────────────────
export const analyticsApi = {
  dashboard: () => api.get('/analytics/dashboard'),
  projectTrends: (days?: number) => api.get('/analytics/projects/trends', { params: { days } }),
  pipelineFunnel: () => api.get('/analytics/pipeline/funnel'),
  investorBreakdown: () => api.get('/analytics/investors/breakdown'),
};

// ── Events ──────────────────────────────────────────────────────────────
export const eventsApi = {
  list: (params?: any) => api.get('/events', { params }),
  get: (id: number) => api.get(`/events/${id}`),
  create: (data: any) => api.post('/events', data),
  update: (id: number, data: any) => api.put(`/events/${id}`, data),
  delete: (id: number) => api.delete(`/events/${id}`),
  rsvp: (id: number, status: string) => api.post(`/events/${id}/rsvp`, { status }),
};

// ── Users ───────────────────────────────────────────────────────────────
export const usersApi = {
  list: (params?: any) => api.get('/users', { params }),
  get: (id: number) => api.get(`/users/${id}`),
  create: (data: any) => api.post('/users', data),
  update: (id: number, data: any) => api.put(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
  activate: (id: number) => api.post(`/users/${id}/activate`),
  deactivate: (id: number) => api.post(`/users/${id}/deactivate`),
  stats: () => api.get('/users/stats/summary'),
};

// ── Integrations ─────────────────────────────────────────────────────────
export const integrationsApi = {
  available: () => api.get('/integrations/available'),
  list: () => api.get('/integrations'),
  create: (data: any) => api.post('/integrations', data),
  update: (id: number, data: any) => api.put(`/integrations/${id}`, data),
  test: (id: number) => api.post(`/integrations/${id}/test`),
  delete: (id: number) => api.delete(`/integrations/${id}`),
};

// ── PIS / PESTEL / EIN ───────────────────────────────────────────────────
export const pisApi = {
  getByProject: (projectId: number) => api.get(`/pis/project/${projectId}`),
  create: (data: any) => api.post('/pis', data),
  update: (projectId: number, data: any) => api.put(`/pis/project/${projectId}`, data),
  generateAI: (projectId: number) => api.post(`/pis/project/${projectId}/generate-ai`),
};
export const pestelApi = {
  getByProject: (projectId: number) => api.get(`/pestel/project/${projectId}`),
  create: (data: any) => api.post('/pestel', data),
  update: (projectId: number, data: any) => api.put(`/pestel/project/${projectId}`, data),
  generateAI: (projectId: number) => api.post(`/pestel/project/${projectId}/generate-ai`),
};
export const einApi = {
  getByProject: (projectId: number) => api.get(`/ein/project/${projectId}`),
  create: (data: any) => api.post('/ein', data),
  update: (projectId: number, data: any) => api.put(`/ein/project/${projectId}`, data),
  generateAI: (projectId: number) => api.post(`/ein/project/${projectId}/generate-ai`),
};

// ── AI Chat ──────────────────────────────────────────────────────────────
export const aiApi = {
  chat: (question: string, context = '') => api.post('/ai/chat', { question, context }),
};
