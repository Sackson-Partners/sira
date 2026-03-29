import apiClient, { tokenStorage } from './client';

export interface LoginRequest {
  username: string;
  password: string;
  device_id?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
}

export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  organization_id?: number;
}

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  // OAuth2 form-encoded
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  const { data } = await apiClient.post<TokenResponse>('/auth/token', formData.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  tokenStorage.set('access_token', data.access_token);
  if (data.refresh_token) {
    tokenStorage.set('refresh_token', data.refresh_token);
  }

  return data;
}

export async function logout(): Promise<void> {
  try {
    const refreshToken = tokenStorage.getString('refresh_token');
    if (refreshToken) {
      await apiClient.post('/auth/logout', { refresh_token: refreshToken });
    }
  } finally {
    tokenStorage.delete('access_token');
    tokenStorage.delete('refresh_token');
  }
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const { data } = await apiClient.get<CurrentUser>('/auth/me');
  return data;
}
