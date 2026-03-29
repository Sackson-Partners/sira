export type UserRole =
  | 'super_admin'
  | 'admin'
  | 'org_admin'
  | 'manager'
  | 'supervisor'
  | 'operator'
  | 'analyst'
  | 'security_lead'
  | 'viewer'
  | 'api_client';

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  role: UserRole;
  permissions: string[];
  organization_id: number | null;
  is_verified: boolean;
  must_change_password: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  super_admin: 'Super Admin',
  admin: 'Administrator',
  org_admin: 'Org Admin',
  manager: 'Manager',
  supervisor: 'Supervisor',
  operator: 'Operator',
  analyst: 'Analyst',
  security_lead: 'Security Lead',
  viewer: 'Viewer',
  api_client: 'API Client',
};

export const ADMIN_ROLES: UserRole[] = ['super_admin', 'admin'];
export const ORG_ADMIN_ROLES: UserRole[] = ['super_admin', 'admin', 'org_admin'];
export const MANAGER_ROLES: UserRole[] = ['super_admin', 'admin', 'org_admin', 'manager', 'supervisor'];
