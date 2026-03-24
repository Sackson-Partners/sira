'use client';

import { useEffect, useState } from 'react';
import { usersApi } from '../../../lib/api';

type UserRole = 'admin' | 'analyst' | 'ic_member' | 'gov_partner' | 'epc' | 'investor' | 'viewer';

interface AIPUser {
  id: string;
  email: string;
  full_name: string | null;
  organisation: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
}

const ROLE_COLORS: Record<string, string> = {
  admin:       'bg-red-100 text-red-800',
  analyst:     'bg-blue-100 text-blue-800',
  ic_member:   'bg-purple-100 text-purple-800',
  gov_partner: 'bg-green-100 text-green-800',
  epc:         'bg-yellow-100 text-yellow-800',
  investor:    'bg-teal-100 text-teal-800',
  viewer:      'bg-gray-100 text-gray-700',
};

const ROLES: UserRole[] = ['admin', 'analyst', 'ic_member', 'gov_partner', 'epc', 'investor', 'viewer'];

export default function UsersPage() {
  const [users, setUsers] = useState<AIPUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState<AIPUser | null>(null);
  const [newForm, setNewForm] = useState({ email: '', password: '', full_name: '', organisation: '', role: 'analyst' });
  const [editForm, setEditForm] = useState({ full_name: '', organisation: '', role: '', is_active: true });
  const [stats, setStats] = useState<any>(null);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const params: any = {};
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      const data = await usersApi.listUsers(params);
      setUsers(data as unknown as AIPUser[]);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to load users. You may need admin access.';
      console.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await usersApi.getStats();
      setStats(data);
    } catch {
      // Non-admin users won't see stats
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [search, roleFilter]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await usersApi.createUser(newForm);
      setShowNewModal(false);
      setNewForm({ email: '', password: '', full_name: '', organisation: '', role: 'analyst' });
      fetchUsers();
      fetchStats();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create user');
    }
  };

  const openEdit = (user: AIPUser) => {
    setEditingUser(user);
    setEditForm({ full_name: user.full_name || '', organisation: user.organisation || '', role: user.role, is_active: user.is_active });
    setShowEditModal(true);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await usersApi.updateUser(editingUser.id, editForm as any);
      setShowEditModal(false);
      fetchUsers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleDelete = async (user: AIPUser) => {
    if (!confirm(`Delete user ${user.email}? This cannot be undone.`)) return;
    try {
      await usersApi.deleteUser(user.id);
      fetchUsers();
      fetchStats();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete user');
    }
  };

  const toggleActive = async (user: AIPUser) => {
    try {
      if (user.is_active) {
        await usersApi.deactivateUser(user.id);
      } else {
        await usersApi.activateUser(user.id);
      }
      fetchUsers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleVerify = async (user: AIPUser) => {
    try {
      await usersApi.verifyUser(user.id);
      fetchUsers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to verify user');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Users</h1>
          <p className="text-gray-500 mt-1">Manage platform access and roles</p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          + Add User
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <p className="text-xs text-gray-500 uppercase font-medium">Total</p>
            <p className="text-3xl font-bold text-gray-900">{stats.total}</p>
          </div>
          <div className="bg-green-50 rounded-xl border border-green-100 p-4">
            <p className="text-xs text-green-500 uppercase font-medium">Active</p>
            <p className="text-3xl font-bold text-green-700">{stats.active}</p>
          </div>
          <div className="bg-blue-50 rounded-xl border border-blue-100 p-4">
            <p className="text-xs text-blue-500 uppercase font-medium">Verified</p>
            <p className="text-3xl font-bold text-blue-700">{stats.verified}</p>
          </div>
          <div className="bg-red-50 rounded-xl border border-red-100 p-4">
            <p className="text-xs text-red-500 uppercase font-medium">Inactive</p>
            <p className="text-3xl font-bold text-red-700">{stats.inactive}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search by name, email, organisation..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Roles</option>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading users...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['Name', 'Email', 'Role', 'Organisation', 'Status', 'Verified', 'Actions'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-gray-400">
                    No users found. Admin role required to view this page.
                  </td>
                </tr>
              )}
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{u.full_name || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${ROLE_COLORS[u.role] || 'bg-gray-100 text-gray-600'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{u.organisation || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${u.is_verified ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>
                      {u.is_verified ? '✓ Verified' : 'Pending'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => openEdit(u)} className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => toggleActive(u)} className="text-xs text-orange-600 hover:underline">
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      {!u.is_verified && (
                        <button onClick={() => handleVerify(u)} className="text-xs text-green-600 hover:underline">Verify</button>
                      )}
                      <button onClick={() => handleDelete(u)} className="text-xs text-red-600 hover:underline">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold">Add New User</h2>
              <button onClick={() => setShowNewModal(false)} className="text-gray-400 text-2xl leading-none">×</button>
            </div>
            <form onSubmit={handleCreateUser} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input type="email" value={newForm.email} onChange={(e) => setNewForm({ ...newForm, email: e.target.value })} required className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
                <input type="password" value={newForm.password} onChange={(e) => setNewForm({ ...newForm, password: e.target.value })} required className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input value={newForm.full_name} onChange={(e) => setNewForm({ ...newForm, full_name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Organisation</label>
                <input value={newForm.organisation} onChange={(e) => setNewForm({ ...newForm, organisation: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select value={newForm.role} onChange={(e) => setNewForm({ ...newForm, role: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewModal(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
                <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold">Edit User: {editingUser.email}</h2>
              <button onClick={() => setShowEditModal(false)} className="text-gray-400 text-2xl leading-none">×</button>
            </div>
            <form onSubmit={handleUpdateUser} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input value={editForm.full_name} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Organisation</label>
                <input value={editForm.organisation} onChange={(e) => setEditForm({ ...editForm, organisation: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select value={editForm.role} onChange={(e) => setEditForm({ ...editForm, role: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="is_active" checked={editForm.is_active} onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })} />
                <label htmlFor="is_active" className="text-sm text-gray-700">Active</label>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowEditModal(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
                <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
