import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { Goal, GoalMilestone, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

const categoryColour: Record<string, string> = {
  career:      'bg-purple-100 text-purple-700',
  technical:   'bg-blue-100   text-blue-700',
  personal:    'bg-pink-100   text-pink-700',
  academic:    'bg-orange-100 text-orange-700',
  networking:  'bg-green-100  text-green-700',
  other:       'bg-gray-100   text-gray-600',
};

const statusColour: Record<string, string> = {
  active:    'bg-green-100  text-green-700',
  completed: 'bg-purple-100 text-purple-700',
  paused:    'bg-yellow-100 text-yellow-700',
};

const statusLabel: Record<string, string> = {
  active:    'Active',
  completed: 'Completed',
  paused:    'Acknowledged',
};

const CATEGORIES = ['career', 'technical', 'personal', 'academic', 'networking', 'other'];

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-purple-50 rounded-full h-1.5">
        <div className="bg-gradient-brand-soft h-1.5 rounded-full transition-all" style={{ width: `${value}%` }} />
      </div>
      <span className="text-[10px] font-semibold text-navy-500/50 w-8 text-right">{value}%</span>
    </div>
  );
}

// ── Milestone item ────────────────────────────────────────────────────────────
function MilestoneItem({ milestone, onToggle, onDelete, readOnly = false }: {
  milestone: GoalMilestone;
  onToggle: () => void;
  onDelete: () => void;
  readOnly?: boolean;
}) {
  return (
    <div className="flex items-center gap-2.5 group py-1">
      <button
        onClick={readOnly ? undefined : onToggle}
        disabled={readOnly}
        className={`w-4 h-4 rounded border-2 flex-shrink-0 flex items-center justify-center transition-all ${milestone.is_completed ? 'bg-pink-500 border-pink-500' : 'border-purple-200'} ${readOnly ? 'cursor-default' : 'hover:border-pink-500'}`}
      >
        {milestone.is_completed && (
          <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </button>
      <span className={`text-xs flex-1 min-w-0 break-words ${milestone.is_completed ? 'line-through text-navy-500/30' : 'text-navy-500/70'}`}>
        {milestone.title}
      </span>
      {milestone.due_date && (
        <span className="text-[10px] text-navy-500/30 flex-shrink-0">
          {new Date(milestone.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
        </span>
      )}
      {!readOnly && (
        <button onClick={onDelete} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 transition-all">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

// ── Goal card ─────────────────────────────────────────────────────────────────
function GoalCard({ goal, currentUserId }: { goal: Goal; currentUserId?: number }) {
  const queryClient = useQueryClient();
  const isOwn = !currentUserId || goal.user === currentUserId;
  const [expanded, setExpanded] = useState(false);
  const [newMilestone, setNewMilestone] = useState('');
  const [milestoneDue, setMilestoneDue] = useState('');

  const updateGoal = useMutation({
    mutationFn: (data: Partial<Goal>) => api.patch(`/goals/goals/${goal.id}/`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const addMilestone = useMutation({
    mutationFn: () => api.post('/goals/milestones/', { goal: goal.id, title: newMilestone, due_date: milestoneDue || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      setNewMilestone(''); setMilestoneDue('');
    },
  });

  const toggleMilestone = useMutation({
    mutationFn: (m: GoalMilestone) => api.patch(`/goals/milestones/${m.id}/`, { is_completed: !m.is_completed }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const deleteMilestone = useMutation({
    mutationFn: (id: number) => api.delete(`/goals/milestones/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const deleteGoal = useMutation({
    mutationFn: () => api.delete(`/goals/goals/${goal.id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  return (
    <div className={`bg-white rounded-2xl shadow-card transition-all ${expanded ? 'ring-1 ring-purple-500/20' : ''}`}>
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1 flex-wrap">
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${categoryColour[goal.category]}`}>{goal.category}</span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${statusColour[goal.status]}`}>{statusLabel[goal.status] ?? goal.status}</span>
              {!isOwn && (
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700">
                  Scholar: {goal.user_name}
                </span>
              )}
              {goal.due_date && (
                <span className="text-[10px] text-navy-500/40">
                  Due {new Date(goal.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                </span>
              )}
            </div>
            <h3 className="font-bold text-sm text-navy-500 break-words">{goal.title}</h3>
            {goal.description && <p className="text-xs text-navy-500/50 mt-0.5 line-clamp-2">{goal.description}</p>}
          </div>
          {isOwn && (
            <div className="flex items-center gap-1 flex-shrink-0">
              {goal.status === 'active' && (
                <button onClick={() => updateGoal.mutate({ status: 'paused' })}
                  className="text-[10px] font-semibold px-2 py-1 rounded-lg bg-yellow-50 text-yellow-700 hover:bg-yellow-100 transition-colors">
                  ✓ Acknowledge
                </button>
              )}
              {goal.status !== 'completed' && (
                <button onClick={() => updateGoal.mutate({ status: 'completed' })}
                  className="text-[10px] font-semibold px-2 py-1 rounded-lg bg-green-50 text-green-600 hover:bg-green-100 transition-colors">
                  ✓ Mark Complete
                </button>
              )}
              <button onClick={() => deleteGoal.mutate()}
                className="text-navy-500/40 hover:text-red-500 transition-colors p-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <ProgressBar value={goal.progress_percent} />

        {goal.milestone_count > 0 && (
          <p className="text-[10px] text-navy-500/40 mt-1">
            {goal.completed_milestone_count} / {goal.milestone_count} milestones complete
          </p>
        )}

        <button onClick={() => setExpanded(v => !v)}
          className="text-xs font-semibold text-pink-500 hover:underline mt-3 flex items-center gap-1">
          {expanded ? 'Hide' : 'Milestones'}
          <svg className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {expanded && (
        <div className="border-t border-purple-50 px-5 pb-5">
          <div className="pt-3 space-y-0.5">
            {goal.milestones.map(m => (
              <MilestoneItem key={m.id} milestone={m}
                onToggle={() => toggleMilestone.mutate(m)}
                onDelete={() => deleteMilestone.mutate(m.id)}
                readOnly={!isOwn} />
            ))}
          </div>

          {isOwn && (
            <div className="flex gap-2 mt-3 items-end">
              <input
                placeholder="Add a milestone…"
                value={newMilestone}
                onChange={e => setNewMilestone(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && newMilestone.trim() && addMilestone.mutate()}
                className="flex-1 border border-purple-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors"
              />
              <label className="block text-[10px] font-medium text-navy-500/70">
                Milestone due date
                <input type="date" value={milestoneDue} onChange={e => setMilestoneDue(e.target.value)}
                  className="mt-1 border border-purple-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors w-32" />
              </label>
              <button onClick={() => newMilestone.trim() && addMilestone.mutate()}
                disabled={!newMilestone.trim() || addMilestone.isPending}
                className="text-xs font-semibold bg-pink-500 text-white px-3 py-1.5 rounded-lg hover:bg-pink-600 disabled:opacity-50 transition-colors">
                +
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── New goal form ─────────────────────────────────────────────────────────────
function NewGoalForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('other');
  const [dueDate, setDueDate] = useState('');

  const create = useMutation({
    mutationFn: () => api.post('/goals/goals/', { title, description, category, due_date: dueDate || null }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['goals'] }); onClose(); },
  });

  return (
    <div className="bg-white rounded-2xl shadow-card p-5 mb-6 space-y-3">
      <h3 className="text-sm font-bold text-navy-500">New Goal</h3>
      <input placeholder="Goal title *" value={title} onChange={e => setTitle(e.target.value)}
        className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors" required />
      <textarea rows={2} placeholder="Describe this goal…" value={description} onChange={e => setDescription(e.target.value)}
        className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none" />
      <div className="grid grid-cols-2 gap-3">
        <select value={category} onChange={e => setCategory(e.target.value)}
          className="border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors text-navy-500 capitalize">
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="block text-xs font-medium text-navy-500/70">
          Target completion date
          <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)}
            className="mt-1 w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors" />
        </label>
      </div>
      <div className="flex gap-2 justify-end pt-1">
        <button onClick={onClose} className="text-sm text-navy-500/60 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">Cancel</button>
        <button onClick={() => create.mutate()} disabled={!title.trim() || create.isPending}
          className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors">
          {create.isPending ? 'Creating…' : 'Create goal'}
        </button>
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function GoalsPage() {
  const { user } = useAuth();
  const [showNew, setShowNew] = useState(false);
  // ISS-G: default to 'all' so Acknowledged (paused) goals are never hidden.
  const [filterStatus, setFilterStatus] = useState('');
  // P3-4: sort control - default matches the backend's own default (-created_at).
  const [ordering, setOrdering] = useState('');

  const params = new URLSearchParams();
  if (filterStatus) params.set('status', filterStatus);
  if (ordering) params.set('ordering', ordering);

  const { data, isLoading } = useQuery<PaginatedResponse<Goal>>({
    queryKey: ['goals', filterStatus, ordering],
    queryFn: () => api.get(`/goals/goals/?${params.toString()}`).then(r => r.data),
  });

  const activeCount = data?.results?.filter(g => g.status === 'active').length ?? 0;
  const completedCount = data?.results?.filter(g => g.status === 'completed').length ?? 0;
  const avgProgress = data?.results?.length
    ? Math.round(data.results.reduce((acc, g) => acc + g.progress_percent, 0) / data.results.length)
    : 0;

  return (
    <div>
      {/* Header */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-8 mb-8 shadow-brand">
        <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full bg-white/5" />
        <div className="relative z-10 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1">Development</p>
            <h1 className="text-2xl font-extrabold">Goals & Milestones</h1>
            <p className="mt-1 text-white/60 text-sm">Track your progress through the programme.</p>
          </div>
          <div className="flex gap-4 text-center">
            <div><p className="text-2xl font-extrabold">{activeCount}</p><p className="text-xs text-white/60">Active</p></div>
            <div><p className="text-2xl font-extrabold">{completedCount}</p><p className="text-xs text-white/60">Completed</p></div>
            <div><p className="text-2xl font-extrabold">{avgProgress}%</p><p className="text-xs text-white/60">Avg progress</p></div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div className="flex gap-1 bg-white rounded-xl shadow-card p-1">
          {[
            { value: 'active', label: 'Active' },
            { value: 'paused', label: 'Acknowledged' },
            { value: 'completed', label: 'Completed' },
            { value: '', label: 'All' },
          ].map(({ value, label }) => (
            <button key={value} onClick={() => setFilterStatus(value)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-all ${filterStatus === value ? 'bg-gradient-brand text-white' : 'text-navy-500/60 hover:text-navy-500'}`}>
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs font-medium text-navy-500/60">
            Sort
            <select value={ordering} onChange={e => setOrdering(e.target.value)}
              className="border border-purple-200 rounded-lg px-2.5 py-1.5 text-xs text-navy-500 focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors">
              <option value="">Newest first</option>
              <option value="due_date">Due date (soonest first)</option>
              <option value="-due_date">Due date (latest first)</option>
            </select>
          </label>
          <button onClick={() => setShowNew(v => !v)}
            className="text-sm font-semibold bg-pink-500 text-white px-5 py-2.5 rounded-xl hover:bg-pink-600 transition-colors shadow-brand">
            + New goal
          </button>
        </div>
      </div>

      {showNew && <NewGoalForm onClose={() => setShowNew(false)} />}

      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">
          {filterStatus ? `${filterStatus.charAt(0).toUpperCase() + filterStatus.slice(1)} Goals` : 'All Goals'}
        </h2>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>
      ) : !data?.results?.length ? (
        <div className="text-center py-16 text-sm text-navy-500/40">
          {filterStatus === 'active' ? 'No active goals yet.' : 'No goals found.'}
          <button onClick={() => setShowNew(true)} className="text-pink-500 font-semibold hover:underline ml-1">Create your first goal.</button>
        </div>
      ) : (
        <div className="space-y-3">
          {data.results.map(g => <GoalCard key={g.id} goal={g} currentUserId={user?.id} />)}
        </div>
      )}
    </div>
  );
}
