/**
 * SIRA API Client — Axios instance with JWT auth interceptors
 */
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { MMKV } from 'react-native-mmkv';

const tokenStorage = new MMKV({ id: 'sira-auth' });

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'https://api.sira.io/api/v1';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Attach access token to every request
apiClient.interceptors.request.use(config => {
  const token = tokenStorage.getString('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401: attempt token refresh, then retry once
apiClient.interceptors.response.use(
  res => res,
  async error => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = tokenStorage.getString('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');

        const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh`, {
          refresh_token: refreshToken,
        });

        tokenStorage.set('access_token', data.access_token);
        if (data.refresh_token) {
          tokenStorage.set('refresh_token', data.refresh_token);
        }

        return apiClient(originalRequest);
      } catch {
        tokenStorage.delete('access_token');
        tokenStorage.delete('refresh_token');
        // Navigation to login handled by auth store subscriber
      }
    }
    return Promise.reject(error);
  }
);

export { tokenStorage };
export default apiClient;
