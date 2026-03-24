import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { eventsApi } from '../services/api';
import toast from 'react-hot-toast';

export default function Events() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [upcoming, setUpcoming] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['events', upcoming],
    queryFn: () => eventsApi.list({ upcoming }).then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => eventsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['events'] }); toast.success('Event deleted'); },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
        <div className="flex gap-2">
          <button onClick={() => setUpcoming(!upcoming)} className={`px-3 py-2 border rounded-lg text-sm ${upcoming ? 'bg-blue-50 border-blue-300 text-blue-700' : 'text-gray-600'}`}>
            {upcoming ? 'All Events' : 'Upcoming Only'}
          </button>
          <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            + New Event
          </button>
        </div>
      </div>
      {isLoading ? <div className="text-center py-12 text-gray-400">Loading events...</div> : (
        <div className="space-y-3">
          {data?.items?.length === 0 && <div className="text-center py-12 text-gray-400 bg-white rounded-xl border">No events yet.</div>}
          {data?.items?.map((e: any) => (
            <div key={e.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900">{e.title}</h3>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full capitalize">{e.event_type?.replace('_', ' ')}</span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  📅 {new Date(e.start_date).toLocaleString()}
                  {e.location && ` · 📍 ${e.location}`}
                  {e.is_virtual && ` · 💻 Virtual`}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => eventsApi.rsvp(e.id, 'confirmed').then(() => toast.success('RSVP confirmed'))} className="text-xs text-green-600 hover:underline">RSVP</button>
                <button onClick={() => { if (confirm('Delete?')) deleteMutation.mutate(e.id); }} className="text-xs text-red-600 hover:underline">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {showForm && <EventModal onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); qc.invalidateQueries({ queryKey: ['events'] }); }} />}
    </div>
  );
}

function EventModal({ onClose, onSaved }: any) {
  const [form, setForm] = useState({ title: '', event_type: 'other', start_date: '', end_date: '', location: '', is_virtual: false, virtual_link: '', description: '' });
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await eventsApi.create(form);
      toast.success('Event created');
      onSaved();
    } catch (err: any) { toast.error(err?.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b"><h2 className="text-xl font-bold">New Event</h2><button onClick={onClose} className="text-gray-400 text-2xl">×</button></div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div><label className="block text-sm font-medium mb-1">Title *</label><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required className="w-full border rounded-lg px-3 py-2 text-sm" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium mb-1">Type</label><select value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">{['webinar','roadshow','lp_meeting','ic_meeting','site_visit','conference','closing','other'].map((t) => <option key={t}>{t}</option>)}</select></div>
            <div><label className="block text-sm font-medium mb-1">Start Date *</label><input type="datetime-local" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required className="w-full border rounded-lg px-3 py-2 text-sm" /></div>
            <div><label className="block text-sm font-medium mb-1">End Date</label><input type="datetime-local" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></div>
            <div><label className="block text-sm font-medium mb-1">Location</label><input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></div>
          </div>
          <div className="flex items-center gap-2"><input type="checkbox" id="virtual" checked={form.is_virtual} onChange={(e) => setForm({ ...form, is_virtual: e.target.checked })} /><label htmlFor="virtual" className="text-sm">Virtual event</label></div>
          {form.is_virtual && <div><label className="block text-sm font-medium mb-1">Virtual Link</label><input value={form.virtual_link} onChange={(e) => setForm({ ...form, virtual_link: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></div>}
          <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg text-sm">Cancel</button><button type="submit" disabled={loading} className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">{loading ? 'Creating...' : 'Create'}</button></div>
        </form>
      </div>
    </div>
  );
}
