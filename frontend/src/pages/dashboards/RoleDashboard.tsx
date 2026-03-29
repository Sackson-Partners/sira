import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { ROLE_LABELS } from '../../types/auth';

const ROLE_CONFIGS: Record<string, {
  title: string;
  stats: Array<{ label: string; value: string }>;
  actions: string[];
}> = {
  super_admin: {
    title: 'Platform Overview',
    stats: [
      { label: 'Organizations', value: '—' },
      { label: 'Total Users', value: '—' },
      { label: 'System Status', value: 'Healthy' },
    ],
    actions: ['Manage Organizations', 'Manage All Users', 'View Audit Logs', 'System Config'],
  },
  admin: {
    title: 'Admin Dashboard',
    stats: [
      { label: 'Total Users', value: '—' },
      { label: 'Active Today', value: '—' },
    ],
    actions: ['Manage Users', 'View Logs'],
  },
  org_admin: {
    title: 'Organization Dashboard',
    stats: [
      { label: 'Team Members', value: '—' },
      { label: 'Active Alerts', value: '—' },
      { label: 'Plan', value: 'Professional' },
    ],
    actions: ['Invite Team Member', 'Manage Roles', 'Org Settings'],
  },
  manager: {
    title: 'Operations Dashboard',
    stats: [
      { label: 'Active Vehicles', value: '—' },
      { label: 'Open Alerts', value: '—' },
      { label: 'Completed Trips', value: '—' },
    ],
    actions: ['View Reports', 'Manage Alerts', 'Team Activity'],
  },
  supervisor: {
    title: 'Supervisor Dashboard',
    stats: [
      { label: 'Active Vehicles', value: '—' },
      { label: 'Open Alerts', value: '—' },
    ],
    actions: ['View Reports', 'Manage Alerts'],
  },
  operator: {
    title: 'Operations View',
    stats: [
      { label: 'Active Vehicles', value: '—' },
      { label: 'My Alerts', value: '—' },
    ],
    actions: ['Acknowledge Alerts', 'Update Status'],
  },
  analyst: {
    title: 'Analytics Dashboard',
    stats: [
      { label: 'Reports Created', value: '—' },
      { label: 'Data Points', value: '—' },
    ],
    actions: ['Create Report', 'Export Data'],
  },
  security_lead: {
    title: 'Security Dashboard',
    stats: [
      { label: 'Open Alerts', value: '—' },
      { label: 'Incidents', value: '—' },
    ],
    actions: ['View Alerts', 'Create Report'],
  },
  viewer: {
    title: 'Overview',
    stats: [
      { label: 'Active Vehicles', value: '—' },
      { label: 'Recent Alerts', value: '—' },
    ],
    actions: ['View Reports', 'View Alerts'],
  },
  api_client: {
    title: 'API Access',
    stats: [{ label: 'API Calls Today', value: '—' }],
    actions: ['View Documentation'],
  },
};

const RoleDashboard: React.FC = () => {
  const { user } = useAuth();
  if (!user) return null;

  const config = ROLE_CONFIGS[user.role] ?? ROLE_CONFIGS.viewer;
  const roleLabel = ROLE_LABELS[user.role] ?? user.role;
  const showPermissions = user.role === 'super_admin' || user.role === 'admin';

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <p className="text-gray-400 text-sm mb-1">
            Welcome back, <span className="text-white">{user.full_name || user.username}</span>
          </p>
          <h1 className="text-white text-2xl font-bold">{config.title}</h1>
        </div>
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-900/50 text-blue-300 border border-blue-800">
          {roleLabel}
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {config.stats.map((stat, i) => (
          <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-1">{stat.label}</p>
            <p className="text-2xl font-bold text-blue-400">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <h2 className="text-white font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          {config.actions.map((action, i) => (
            <button
              key={i}
              className="bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium py-2 px-4 rounded-lg transition-colors border border-gray-700"
            >
              {action}
            </button>
          ))}
        </div>
      </div>

      {showPermissions && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-gray-400 text-sm font-medium mb-3">
            Permissions ({user.permissions?.length ?? 0})
          </h2>
          <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
            {user.permissions?.map(p => (
              <span key={p} className="text-xs bg-gray-800 text-gray-400 px-2 py-1 rounded font-mono">
                {p}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RoleDashboard;
