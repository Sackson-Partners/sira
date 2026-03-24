import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { pipelineApi } from '../services/api';
import toast from 'react-hot-toast';

const STAGES = ['sourcing','initial_review','due_diligence','ic_review','term_sheet','negotiation','closing','closed_won','closed_lost','on_hold'];
const STAGE_COLORS: any = {
  sourcing: 'bg-gray-100',
  initial_review: 'bg-blue-50',
  due_diligence: 'bg-yellow-50',
  ic_review: 'bg-purple-50',
  term_sheet: 'bg-indigo-50',
  negotiation: 'bg-orange-50',
  closing: 'bg-green-50',
  closed_won: 'bg-green-100',
  closed_lost: 'bg-red-100',
  on_hold: 'bg-gray-200',
};

export default function Pipeline() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [view, setView] = useState<'kanban' | 'list'>('kanban');

  const { data, isLoading } = useQuery({
    queryKey: ['pipeline'],
    queryFn: () => pipelineApi.list({ limit: 500 }).then((r) => r.data),
  });

  const moveStageMutation = useMutation({
    mutationFn: ({ id, stage }: any) => pipelineApi.moveStage(id, stage),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline'] }),
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => pipelineApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['pipeline'] }); toast.success('Deal deleted'); },
  });

  const fmtUSD = (v: number) => v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : `$${v.toLocaleString()}`;

  if (isLoading) return <div className="text-center py-12 text-gray-400">Loading pipeline...</div>;

  const kanban = data?.kanban || {};

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
        <div className="flex gap-2">
          <button onClick={() => setView(view === 'kanban' ? 'list' : 'kanban')} className="px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">
            {view === 'kanban' ? '≡ List' : '⬜ Kanban'}
          </button>
          <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            + New Deal
          </button>
        </div>
      </div>

      {view === 'kanban' ? (
        <div className="overflow-x-auto">
          <div className="flex gap-3 min-w-max">
            {STAGES.slice(0, 8).map((stage) => (
              <div key={stage} className={`w-48 rounded-xl ${STAGE_COLORS[stage]} border border-gray-200 p-3`}>
                <h3 className="text-xs font-semibold text-gray-600 uppercase mb-2">{stage.replace('_', ' ')} <span className="text-gray-400">({kanban[stage]?.length || 0})</span></h3>
                <div className="space-y-2">
                  {(kanban[stage] || []).map((deal: any) => (
                    <div key={deal.id} className="bg-white rounded-lg p-2 shadow-sm border border-gray-100">
                      <p className="text-xs font-medium text-gray-800 truncate">{deal.name}</p>
                      {deal.deal_size && <p className="text-xs text-gray-500 mt-1">{fmtUSD(deal.deal_size)}</p>}
                      <div className="flex gap-1 mt-2">
                        <button onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(deal.id); }} className="text-xs text-red-400 hover:text-red-600">✕</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>{['Name','Stage','Size','Probability','Expected Close','Actions'].map((h) => <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data?.items?.map((deal: any) => (
                <tr key={deal.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{deal.name}</td>
                  <td className="px-4 py-3"><span className="capitalize text-xs bg-gray-100 px-2 py-1 rounded-full">{deal.stage?.replace('_', ' ')}</span></td>
                  <td className="px-4 py-3 text-gray-600">{deal.deal_size ? fmtUSD(deal.deal_size) : '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{deal.probability}%</td>
                  <td className="px-4 py-3 text-gray-600">{deal.expected_close_date ? new Date(deal.expected_close_date).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(deal.id); }} className="text-xs text-red-600 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && <DealModal onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); qc.invalidateQueries({ queryKey: ['pipeline'] }); }} />}
    </div>
  );
}

function DealModal({ onClose, onSaved }: any) {
  const [form, setForm] = useState({ name: '', stage: 'sourcing', deal_size: '', currency: 'USD', probability: '0', description: '', expected_close_date: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await pipelineApi.create({ ...form, deal_size: form.deal_size ? Number(form.deal_size) : null, probability: Number(form.probability) });
      toast.success('Deal created');
      onSaved();
    } catch (err: any) { toast.error(err?.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold">New Deal</h2>
          <button onClick={onClose} className="text-gray-400 text-2xl">×</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Deal Name *</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Stage</label>
              <select value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                {STAGES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Probability (%)</label>
              <input type="number" min="0" max="100" value={form.probability} onChange={(e) => setForm({ ...form, probability: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Deal Size</label>
              <input type="number" value={form.deal_size} onChange={(e) => setForm({ ...form, deal_size: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Expected Close</label>
              <input type="date" value={form.expected_close_date} onChange={(e) => setForm({ ...form, expected_close_date: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg text-sm">Cancel</button>
            <button type="submit" disabled={loading} className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{loading ? 'Creating...' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
