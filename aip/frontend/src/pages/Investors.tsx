import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { investorsApi } from '../services/api';
import toast from 'react-hot-toast';

export default function Investors() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editInvestor, setEditInvestor] = useState<any>(null);
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['investors', search],
    queryFn: () => investorsApi.list({ search: search || undefined }).then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => investorsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['investors'] }); toast.success('Investor deleted'); },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Delete failed'),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Investors</h1>
        <button onClick={() => { setEditInvestor(null); setShowForm(true); }} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + New Investor
        </button>
      </div>
      <input type="text" placeholder="Search investors..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" />

      {isLoading ? <div className="text-center py-12 text-gray-400">Loading...</div> : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{['Name','Type','Status','Email','Country','AUM','KYC','Actions'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data?.items?.length === 0 && <tr><td colSpan={8} className="py-8 text-center text-gray-400">No investors yet.</td></tr>}
              {data?.items?.map((inv: any) => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{inv.name}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{inv.investor_type?.replace('_', ' ')}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs ${inv.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>{inv.status}</span></td>
                  <td className="px-4 py-3 text-gray-600">{inv.email || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.country || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{inv.aum ? `$${(inv.aum/1e6).toFixed(0)}M` : '—'}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs ${inv.kyc_status === 'approved' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{inv.kyc_status}</span></td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => { setEditInvestor(inv); setShowForm(true); }} className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(inv.id); }} className="text-xs text-red-600 hover:underline">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showForm && <InvestorModal investor={editInvestor} onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); qc.invalidateQueries({ queryKey: ['investors'] }); }} />}
    </div>
  );
}

function InvestorModal({ investor, onClose, onSaved }: any) {
  const [form, setForm] = useState({
    name: investor?.name || '', investor_type: investor?.investor_type || 'individual',
    status: investor?.status || 'prospect', email: investor?.email || '', phone: investor?.phone || '',
    country: investor?.country || '', aum: investor?.aum || '', investment_min: investor?.investment_min || '',
    investment_max: investor?.investment_max || '', currency: investor?.currency || 'USD',
    risk_appetite: investor?.risk_appetite || '', notes: investor?.notes || '',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { ...form, aum: form.aum ? Number(form.aum) : null, investment_min: form.investment_min ? Number(form.investment_min) : null, investment_max: form.investment_max ? Number(form.investment_max) : null };
      if (investor?.id) { await investorsApi.update(investor.id, payload); toast.success('Updated'); }
      else { await investorsApi.create(payload); toast.success('Created'); }
      onSaved();
    } catch (err: any) { toast.error(err?.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold">{investor ? 'Edit Investor' : 'New Investor'}</h2>
          <button onClick={onClose} className="text-gray-400 text-2xl">×</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 grid grid-cols-2 gap-4">
          {[['name','Name',true],['email','Email',false],['phone','Phone',false],['country','Country',false],['aum','AUM (USD)',false],['investment_min','Min Investment',false],['investment_max','Max Investment',false]].map(([k, l, req]: any) => (
            <div key={k}>
              <label className="block text-sm font-medium mb-1">{l}{req && ' *'}</label>
              <input value={(form as any)[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required={req} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          ))}
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select value={form.investor_type} onChange={(e) => setForm({ ...form, investor_type: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
              {['individual','family_office','institutional','corporate','fund','pension','sovereign','endowment'].map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
              {['prospect','onboarding','active','inactive','blocked'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div className="col-span-2 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg text-sm">Cancel</button>
            <button type="submit" disabled={loading} className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{loading ? 'Saving...' : 'Save'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
