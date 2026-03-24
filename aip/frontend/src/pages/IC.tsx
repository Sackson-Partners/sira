'use client';

import { useEffect, useState } from 'react';
import { icApi, projectsApi, einApi, ICCommittee, Project } from '../../../lib/api';

type VoteOption = 'approve' | 'reject' | 'abstain' | 'defer';

const VOTE_COLORS: Record<string, string> = {
  approve:  'bg-green-100 text-green-800',
  reject:   'bg-red-100 text-red-800',
  abstain:  'bg-gray-100 text-gray-700',
  defer:    'bg-yellow-100 text-yellow-800',
};

const STATUS_COLORS: Record<string, string> = {
  scheduled:   'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  decided:     'bg-green-100 text-green-800',
};

const OUTCOME_COLORS: Record<string, string> = {
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  deferred: 'bg-yellow-100 text-yellow-800',
};

export default function ICPage() {
  const [committees, setCommittees] = useState<ICCommittee[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showNewModal, setShowNewModal] = useState(false);
  const [selectedCommittee, setSelectedCommittee] = useState<ICCommittee | null>(null);
  const [committeeDetail, setCommitteeDetail] = useState<any>(null);
  const [voteOption, setVoteOption] = useState<VoteOption>('approve');
  const [voteRationale, setVoteRationale] = useState('');
  const [isVoting, setIsVoting] = useState(false);
  const [newForm, setNewForm] = useState({
    project_id: '',
    scheduled_date: '',
    quorum_required: 3,
  });

  const fetchCommittees = async () => {
    try {
      const data = await icApi.listCommittees();
      setCommittees(data);
    } catch (err) {
      console.error('Failed to fetch IC sessions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const data = await projectsApi.list();
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    }
  };

  useEffect(() => {
    fetchCommittees();
    fetchProjects();
  }, []);

  const openCommittee = async (committee: ICCommittee) => {
    try {
      const detail = await icApi.getCommittee(committee.committee_id);
      setCommitteeDetail(detail);
      setSelectedCommittee(committee);
    } catch (err) {
      console.error('Failed to fetch committee detail:', err);
    }
  };

  const handleScheduleIC = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await icApi.createCommittee({
        project_id: parseInt(newForm.project_id),
        scheduled_date: newForm.scheduled_date,
        quorum_required: newForm.quorum_required,
      });
      setShowNewModal(false);
      setNewForm({ project_id: '', scheduled_date: '', quorum_required: 3 });
      fetchCommittees();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to schedule IC session');
    }
  };

  const handleVote = async () => {
    if (!selectedCommittee) return;
    setIsVoting(true);
    try {
      await icApi.submitVote(
        selectedCommittee.committee_id,
        voteOption,
        voteRationale || undefined,
      );
      const updated = await icApi.getCommittee(selectedCommittee.committee_id);
      setCommitteeDetail(updated);
      setVoteRationale('');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to submit vote');
    } finally {
      setIsVoting(false);
    }
  };

  const handleDecide = async (outcome: string) => {
    if (!selectedCommittee) return;
    try {
      await icApi.recordDecision(selectedCommittee.committee_id, outcome);
      const updated = await icApi.getCommittee(selectedCommittee.committee_id);
      setCommitteeDetail(updated);
      fetchCommittees();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to record decision');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Investment Committee (IC)</h1>
          <p className="text-gray-500 mt-1">Schedule IC sessions, submit votes, and record decisions</p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          + Schedule IC Session
        </button>
      </div>

      {/* Sessions list */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading IC sessions...</div>
      ) : committees.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-400 text-lg">No IC sessions scheduled yet.</p>
          <p className="text-gray-400 text-sm mt-1">Click &ldquo;Schedule IC Session&rdquo; to create one.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {committees.map((c: any) => (
            <div
              key={c.committee_id}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-200 cursor-pointer transition-colors"
              onClick={() => openCommittee(c)}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">
                    {c.project_name || `Project #${c.project_id}`}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    IC Session #{c.committee_id}
                    {c.scheduled_date && ` · ${new Date(c.scheduled_date).toLocaleString()}`}
                  </p>
                  <p className="text-sm text-gray-500">
                    Votes: {c.vote_count} / {c.quorum} required
                  </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] || 'bg-gray-100 text-gray-600'}`}>
                    {c.status}
                  </span>
                  {c.outcome && (
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${OUTCOME_COLORS[c.outcome] || 'bg-gray-100 text-gray-600'}`}>
                      {c.outcome}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Schedule Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold">Schedule IC Session</h2>
              <button onClick={() => setShowNewModal(false)} className="text-gray-400 text-2xl leading-none">×</button>
            </div>
            <form onSubmit={handleScheduleIC} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Project *</label>
                <select
                  value={newForm.project_id}
                  onChange={(e) => setNewForm({ ...newForm, project_id: e.target.value })}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Select a project...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.project_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Scheduled Date</label>
                <input
                  type="datetime-local"
                  value={newForm.scheduled_date}
                  onChange={(e) => setNewForm({ ...newForm, scheduled_date: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quorum Required</label>
                <input
                  type="number"
                  min="1"
                  value={newForm.quorum_required}
                  onChange={(e) => setNewForm({ ...newForm, quorum_required: parseInt(e.target.value) })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowNewModal(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600">Cancel</button>
                <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">Schedule</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Committee Detail / Voting Modal */}
      {selectedCommittee && committeeDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold">
                IC Session — {committeeDetail.project_id}
              </h2>
              <button onClick={() => { setSelectedCommittee(null); setCommitteeDetail(null); }} className="text-gray-400 text-2xl leading-none">×</button>
            </div>
            <div className="p-6 space-y-6">
              {/* Vote Summary */}
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Vote Summary</h3>
                <div className="grid grid-cols-4 gap-3">
                  {Object.entries(committeeDetail.vote_summary || {}).map(([k, v]: any) => (
                    <div key={k} className={`rounded-lg p-3 text-center ${VOTE_COLORS[k] || 'bg-gray-50'}`}>
                      <p className="text-2xl font-bold">{v}</p>
                      <p className="text-xs capitalize mt-1">{k}</p>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-gray-500 mt-2">
                  Total votes: {committeeDetail.votes?.length || 0} / Quorum: {committeeDetail.quorum_required}
                  {' '}· {committeeDetail.quorum_met ? '✅ Quorum met' : '⏳ Quorum not yet met'}
                </p>
              </div>

              {/* Existing Votes */}
              {(committeeDetail.votes || []).length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">Individual Votes</h3>
                  <div className="space-y-2">
                    {committeeDetail.votes.map((v: any, i: number) => (
                      <div key={i} className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${VOTE_COLORS[v.vote] || 'bg-gray-100'}`}>{v.vote}</span>
                        <div>
                          <p className="text-xs text-gray-500">Voter #{v.voter_id}</p>
                          {v.rationale && <p className="text-sm text-gray-700 mt-1">{v.rationale}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cast Vote */}
              {committeeDetail.status !== 'decided' && (
                <div className="border-t pt-4">
                  <h3 className="font-semibold text-gray-700 mb-3">Cast Your Vote</h3>
                  <div className="space-y-3">
                    <div className="flex gap-2">
                      {(['approve', 'reject', 'abstain', 'defer'] as VoteOption[]).map((v) => (
                        <button
                          key={v}
                          onClick={() => setVoteOption(v)}
                          className={`flex-1 py-2 rounded-lg text-sm font-medium border capitalize transition-colors ${
                            voteOption === v
                              ? `${VOTE_COLORS[v]} border-current`
                              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          {v}
                        </button>
                      ))}
                    </div>
                    <textarea
                      value={voteRationale}
                      onChange={(e) => setVoteRationale(e.target.value)}
                      placeholder="Rationale (optional)"
                      rows={2}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    />
                    <button
                      onClick={handleVote}
                      disabled={isVoting}
                      className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {isVoting ? 'Submitting...' : 'Submit Vote'}
                    </button>
                  </div>
                </div>
              )}

              {/* Record Decision */}
              {committeeDetail.quorum_met && committeeDetail.status !== 'decided' && (
                <div className="border-t pt-4">
                  <h3 className="font-semibold text-gray-700 mb-3">Record Final Decision</h3>
                  <div className="flex gap-2">
                    {(['approved', 'rejected', 'deferred'] as const).map((outcome) => (
                      <button
                        key={outcome}
                        onClick={() => handleDecide(outcome)}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium capitalize ${OUTCOME_COLORS[outcome]} hover:opacity-90`}
                      >
                        {outcome}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
