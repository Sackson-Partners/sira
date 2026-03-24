import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const nav = [
  { label: 'Dashboard',    path: '/',              icon: '📊' },
  { label: 'Projects',     path: '/projects',      icon: '📁' },
  { label: 'Pipeline',     path: '/pipeline',      icon: '🔀' },
  { label: 'IC',           path: '/ic',            icon: '⚖️' },
  { label: 'Investors',    path: '/investors',     icon: '👥' },
  { label: 'PIS',          path: '/pis',           icon: '📋' },
  { label: 'PESTEL',       path: '/pestel',        icon: '🌍' },
  { label: 'EIN',          path: '/ein',           icon: '💡' },
  { label: 'Data Rooms',   path: '/data-rooms',    icon: '🗄️' },
  { label: 'Deal Rooms',   path: '/deal-rooms',    icon: '🤝' },
  { label: 'Verifications',path: '/verifications', icon: '✅' },
  { label: 'Analytics',    path: '/analytics',     icon: '📈' },
  { label: 'Events',       path: '/events',        icon: '📅' },
  { label: 'Users',        path: '/users',         icon: '👤' },
  { label: 'Integrations', path: '/integrations',  icon: '🔌' },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-56' : 'w-14'} bg-gray-900 text-white flex flex-col transition-all duration-200 shrink-0`}>
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-700">
          {sidebarOpen && <span className="font-bold text-lg text-blue-400">AIP Platform</span>}
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-400 hover:text-white">
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {nav.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-gray-700 transition-colors ${
                pathname === item.path ? 'bg-blue-700 text-white' : 'text-gray-300'
              }`}
            >
              <span className="text-base shrink-0">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-700">
          {sidebarOpen && (
            <div className="text-xs text-gray-400 mb-2">
              <div className="font-medium text-gray-200">{user?.full_name}</div>
              <div className="capitalize">{user?.role}</div>
            </div>
          )}
          <button onClick={handleLogout} className="text-xs text-red-400 hover:text-red-300">
            {sidebarOpen ? 'Logout' : '🚪'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
