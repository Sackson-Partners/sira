import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'

// Token key must match the key used by AuthContext
const TOKEN_STORAGE_KEY = 'sira_access_token'

// API base URL — empty string means same-origin requests.
// Local dev: Vite proxy forwards /api/* to localhost:8000 (see vite.config.ts)
// Production (Vercel): vercel.json rewrites /api/* to Azure Container App
const API_BASE_URL = ''

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear all auth state and redirect to login
      localStorage.removeItem('sira_access_token')
      localStorage.removeItem('sira_refresh_token')
      localStorage.removeItem('sira_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API service functions
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/v1/auth/token', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  getCurrentUser: () => api.get('/api/v1/auth/me'),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
}

export const alertsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/alerts/', { params }),
  getById: (id: number) => api.get(`/api/v1/alerts/${id}`),
  create: (data: any) => api.post('/api/v1/alerts/', data),
  update: (id: number, data: any) => api.put(`/api/v1/alerts/${id}`, data),
  acknowledge: (id: number) => api.post(`/api/v1/alerts/${id}/acknowledge`),
  resolve: (id: number, notes: string) =>
    api.post(`/api/v1/alerts/${id}/resolve`, { resolution_notes: notes }),
  getStats: () => api.get('/api/v1/alerts/stats'),
}

export const casesApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/cases/', { params }),
  getById: (id: number) => api.get(`/api/v1/cases/${id}`),
  create: (data: any) => api.post('/api/v1/cases/', data),
  update: (id: number, data: any) => api.put(`/api/v1/cases/${id}`, data),
  close: (id: number, data: any) => api.post(`/api/v1/cases/${id}/close`, data),
  export: (id: number, format: 'json' | 'pdf' = 'json') =>
    api.get(`/api/v1/cases/${id}/export`, { params: { format } }),
  getStats: () => api.get('/api/v1/cases/stats'),
}

export const movementsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/movements/', { params }),
  getById: (id: number) => api.get(`/api/v1/movements/${id}`),
  create: (data: any) => api.post('/api/v1/movements/', data),
  update: (id: number, data: any) => api.put(`/api/v1/movements/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/movements/${id}`),
}

export const usersApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/users/', { params }),
  getById: (id: number) => api.get(`/api/v1/users/${id}`),
  create: (data: any) => api.post('/api/v1/users/', data),
  update: (id: number, data: any) => api.put(`/api/v1/users/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/users/${id}`),
  activate: (id: number) => api.post(`/api/v1/users/${id}/activate`),
}

export const reportsApi = {
  getDashboard: () => api.get('/api/v1/reports/dashboard'),
  getAlertsSummary: (params?: Record<string, any>) =>
    api.get('/api/v1/reports/alerts/summary', { params }),
  getActivity: (days: number = 7) =>
    api.get('/api/v1/reports/activity', { params: { days } }),
}

export const notificationsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/notifications/', { params }),
  getUnreadCount: () => api.get('/api/v1/notifications/unread-count'),
  markAsRead: (id: number) => api.post(`/api/v1/notifications/${id}/read`),
  markAllAsRead: () => api.post('/api/v1/notifications/read-all'),
  getPreferences: () => api.get('/api/v1/notifications/preferences'),
  updatePreferences: (data: any) => api.put('/api/v1/notifications/preferences', data),
}

export const controlTowerApi = {
  getOverview: () => api.get('/api/v1/control-tower/overview'),
  getMapData: () => api.get('/api/v1/control-tower/map-data'),
  getKpis: (days?: number) =>
    api.get('/api/v1/control-tower/kpis', { params: days !== undefined ? { days } : undefined }),
}

export const vesselsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/vessels/', { params }),
  getById: (id: number) => api.get(`/api/v1/vessels/${id}`),
  getPositions: () => api.get('/api/v1/vessels/positions'),
  create: (data: any) => api.post('/api/v1/vessels/', data),
  update: (id: number, data: any) => api.put(`/api/v1/vessels/${id}`, data),
  updatePosition: (id: number, data: any) => api.put(`/api/v1/vessels/${id}/position`, data),
}

export const portsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/ports/', { params }),
  getById: (id: number) => api.get(`/api/v1/ports/${id}`),
  create: (data: any) => api.post('/api/v1/ports/', data),
  getBerths: (portId: number) => api.get(`/api/v1/ports/${portId}/berths`),
  createBerth: (portId: number, data: any) => api.post(`/api/v1/ports/${portId}/berths`, data),
  getBookings: (params?: Record<string, any>) => api.get('/api/v1/ports/bookings/', { params }),
  createBooking: (data: any) => api.post('/api/v1/ports/bookings/', data),
  updateBooking: (id: number, data: any) => api.put(`/api/v1/ports/bookings/${id}`, data),
  getCongestionSummary: () => api.get('/api/v1/ports/congestion/summary'),
}

export const fleetApi = {
  getAssets: (params?: Record<string, any>) => api.get('/api/v1/fleet/assets/', { params }),
  getAssetById: (id: number) => api.get(`/api/v1/fleet/assets/${id}`),
  createAsset: (data: any) => api.post('/api/v1/fleet/assets/', data),
  updateAsset: (id: number, data: any) => api.put(`/api/v1/fleet/assets/${id}`, data),
  getAvailability: () => api.get('/api/v1/fleet/assets/availability'),
  getUtilization: () => api.get('/api/v1/fleet/assets/utilization'),
  getDispatches: (params?: Record<string, any>) => api.get('/api/v1/fleet/dispatch/', { params }),
  createDispatch: (data: any) => api.post('/api/v1/fleet/dispatch/', data),
  updateDispatch: (id: number, data: any) => api.put(`/api/v1/fleet/dispatch/${id}`, data),
  getMaintenance: (params?: Record<string, any>) =>
    api.get('/api/v1/fleet/maintenance/', { params }),
  createMaintenance: (data: any) => api.post('/api/v1/fleet/maintenance/', data),
  updateMaintenance: (id: number, data: any) =>
    api.put(`/api/v1/fleet/maintenance/${id}`, data),
}

export const corridorsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/corridors/', { params }),
  getById: (id: number) => api.get(`/api/v1/corridors/${id}`),
  create: (data: any) => api.post('/api/v1/corridors/', data),
}

export const shipmentsApi = {
  getAll: (params?: Record<string, any>) => api.get('/api/v1/shipments/', { params }),
  getActive: () => api.get('/api/v1/shipments/active'),
  getAtRisk: (threshold?: number) =>
    api.get('/api/v1/shipments/at-risk', {
      params: threshold !== undefined ? { threshold } : undefined,
    }),
  getById: (id: number) => api.get(`/api/v1/shipments/${id}`),
  create: (data: any) => api.post('/api/v1/shipments/', data),
  update: (id: number, data: any) => api.put(`/api/v1/shipments/${id}`, data),
  getMilestones: (id: number) => api.get(`/api/v1/shipments/${id}/milestones`),
  createMilestone: (id: number, data: any) =>
    api.post(`/api/v1/shipments/${id}/milestones`, data),
  getCustodyEvents: (id: number) => api.get(`/api/v1/shipments/${id}/custody`),
  createCustodyEvent: (id: number, data: any) =>
    api.post(`/api/v1/shipments/${id}/custody`, data),
  getDocuments: (id: number) => api.get(`/api/v1/shipments/${id}/documents`),
  createDocument: (id: number, data: any) =>
    api.post(`/api/v1/shipments/${id}/documents`, data),
  getExceptions: (id: number) => api.get(`/api/v1/shipments/${id}/exceptions`),
  createException: (id: number, data: any) =>
    api.post(`/api/v1/shipments/${id}/exceptions`, data),
}

export const marketApi = {
  getRates: (params?: Record<string, any>) => api.get('/api/v1/market/rates/', { params }),
  getRateBenchmarks: (params?: Record<string, any>) =>
    api.get('/api/v1/market/rates/benchmark', { params }),
  createRate: (data: any) => api.post('/api/v1/market/rates/', data),
  getIndices: (params?: Record<string, any>) => api.get('/api/v1/market/indices/', { params }),
  getLatestIndices: () => api.get('/api/v1/market/indices/latest'),
  getDemurrageRecords: (params?: Record<string, any>) =>
    api.get('/api/v1/market/demurrage/', { params }),
  getDemurrageExposure: () => api.get('/api/v1/market/demurrage/exposure'),
}

// Phase 2: Flespi Telematics
export const telemetryApi = {
  getStatus: () => api.get('/api/v1/telemetry/status'),
  getDevices: () => api.get('/api/v1/telemetry/devices'),
  getDeviceTelemetry: (deviceId: number) =>
    api.get(`/api/v1/telemetry/devices/${deviceId}/telemetry`),
  getDeviceMessages: (deviceId: number, limit?: number) =>
    api.get(`/api/v1/telemetry/devices/${deviceId}/messages`, { params: { limit } }),
  syncDevices: () => api.post('/api/v1/telemetry/sync-devices'),
}

// Phase 2: MarineTraffic AIS
export const aisApi = {
  getStatus: () => api.get('/api/v1/ais/status'),
  getVesselPosition: (mmsi: string) => api.get(`/api/v1/ais/vessel/${mmsi}`),
  getFleetPositions: () => api.get('/api/v1/ais/fleet'),
  getVesselDetails: (imo: string) => api.get(`/api/v1/ais/vessel/${imo}/details`),
  syncPositions: () => api.post('/api/v1/ais/sync-positions'),
}

// Phase 2: AI Intelligence Engine
export const aiApi = {
  getStatus: () => api.get('/api/v1/ai/status'),
  chat: (message: string, history?: Array<{ role: string; content: string }>) =>
    api.post('/api/v1/ai/chat', { message, history }),
  predictETA: (data: {
    origin: string; destination: string; departure_time: string;
    vessel_speed?: number; weather_conditions?: string;
  }) => api.post('/api/v1/ai/predict-eta', data),
  analyzeRisk: (data: { shipment_id?: number; shipment_data?: any }) =>
    api.post('/api/v1/ai/analyze-risk', data),
  demurrageRisk: (vessel_data: any, port_data: any) =>
    api.post('/api/v1/ai/demurrage-risk', { vessel_data, port_data }),
}

// Phase 2: Integration health
export const integrationsApi = {
  getStatus: () => api.get('/health/integrations'),
}
