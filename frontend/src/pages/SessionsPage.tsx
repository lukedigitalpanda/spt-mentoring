import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { MentoringSession, AvailabilitySlot, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

const statusColour: Record<string, string> = {
  pending:   'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-green-100  text-green-700',
  cancelled: 'bg-red-100    text-red-500',
  completed: 'bg-purple-100 text-purple-700',
  no_show:   'bg-gray-100   text-gray-500',
};

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
}
function fmtTime(d: string) {
  return new Date(d).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}
function fmtDateTime(d: string) { return `${fmtDate(d)} at ${fmtTime(d)}`; }

// ── Weekly slot helpers ────────────────────────────────────────────────────────
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const pad = (n: number) => String(n).padStart(2, '0');

function toLocalDT(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Returns YYYY-MM-DD in the user's local timezone (for grouping)
function localDateKey(isoStr: string) {
  const d = new Date(isoStr);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// Build a list of slot datetime pairs from a weekly pattern
function buildWeeklySlots(days: number[], startHHMM: string, endHHMM: string, weeks: number) {
  const [sh, sm] = startHHMM.split(':').map(Number);
  const [eh, em] = endHHMM.split(':').map(Number);
  const now = new Date();

  // Monday of the current week
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const jsDay = today.getDay(); // 0=Sun, 1=Mon…
  const daysFromMonday = jsDay === 0 ? 6 : jsDay - 1;
  const monday = new Date(today);
  monday.setDate(today.getDate() - daysFromMonday);

  const results: { start_time: string; end_time: string }[] = [];
  for (let w = 0; w < weeks; w++) {
    for (const d of [...days].sort((a, b) => a - b)) {
      const base = new Date(monday);
      base.setDate(monday.getDate() + w * 7 + d);
      const start = new Date(base.getFullYear(), base.getMonth(), base.getDate(), sh, sm);
      const end   = new Date(base.getFullYear(), base.getMonth(), base.getDate(), eh, em);
      if (start > now) results.push({ start_time: toLocalDT(start), end_time: toLocalDT(end) });
    }
  }
  return results;
}

function groupBy<T>(arr: T[], key: (item: T) => string): Record<string, T[]> {
  return arr.reduce((acc, item) => {
    const k = key(item);
    (acc[k] ??= []).push(item);
    return acc;
  }, {} as Record<string, T[]>);
}

// ── Feedback form ─────────────────────────────────────────────────────────────
function FeedbackForm({ session, onDone }: { session: MentoringSession; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [rating, setRating] = useState(0);
  const [highlights, setHighlights] = useState('');
  const [improvements, setImprovements] = useState('');
  const [wouldRecommend, setWouldRecommend] = useState<boolean | null>(null);

  const submit = useMutation({
    mutationFn: () => api.post('/sessions/feedback/', {
      session: session.id, rating, highlights, improvements,
      would_recommend: wouldRecommend,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      onDone();
    },
  });

  return (
    <div className="bg-white rounded-2xl shadow-card p-6 space-y-5">
      <h3 className="text-base font-bold text-navy-500">Rate your session</h3>
      <div>
        <p className="text-xs font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Overall rating</p>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map(n => (
            <button key={n} type="button" onClick={() => setRating(n)}
              className={`w-10 h-10 rounded-xl text-lg transition-all ${rating >= n ? 'text-yellow-400' : 'text-gray-300 hover:text-yellow-300'}`}>
              ★
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="text-xs font-semibold text-navy-500/40 uppercase tracking-wider mb-1">What went well?</p>
        <textarea rows={2} value={highlights} onChange={e => setHighlights(e.target.value)}
          className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none"
          placeholder="Highlights from the session…" />
      </div>
      <div>
        <p className="text-xs font-semibold text-navy-500/40 uppercase tracking-wider mb-1">What could improve?</p>
        <textarea rows={2} value={improvements} onChange={e => setImprovements(e.target.value)}
          className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none"
          placeholder="Suggestions for next time…" />
      </div>
      <div>
        <p className="text-xs font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Would you recommend this mentor?</p>
        <div className="flex gap-2">
          {[true, false].map(v => (
            <button key={String(v)} type="button" onClick={() => setWouldRecommend(v)}
              className={`text-xs font-semibold px-4 py-1.5 rounded-lg border transition-all ${wouldRecommend === v ? 'bg-pink-500 text-white border-pink-500' : 'border-purple-100 text-navy-500/60'}`}>
              {v ? 'Yes' : 'No'}
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-2 justify-end pt-2">
        <button onClick={onDone} className="text-sm text-navy-500/60 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">Cancel</button>
        <button
          onClick={() => submit.mutate()}
          disabled={rating === 0 || submit.isPending}
          className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors">
          {submit.isPending ? 'Submitting…' : 'Submit feedback'}
        </button>
      </div>
    </div>
  );
}

// ── Session card ──────────────────────────────────────────────────────────────
function SessionCard({ session, currentUserId, onAction }: {
  session: MentoringSession;
  currentUserId: number;
  onAction: (id: number, action: string) => void;
}) {
  const [showFeedback, setShowFeedback] = useState(false);
  const isMentor = session.mentor === currentUserId;
  const alreadyFeedback = session.feedback.some(f => f.from_user === currentUserId);
  const isUpcoming = new Date(session.start_time) > new Date();
  const isJoinable =
    new Date(session.start_time).getTime() - 5 * 60_000 <= Date.now() &&
    new Date(session.end_time) > new Date();
  const [joining, setJoining] = useState(false);

  return (
    <div className="bg-white rounded-2xl shadow-card p-5">
      {showFeedback ? (
        <FeedbackForm session={session} onDone={() => setShowFeedback(false)} />
      ) : (
        <>
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex-1 min-w-0">
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize mb-1 inline-block ${statusColour[session.status]}`}>
                {session.status.replace('_', ' ')}
              </span>
              <h3 className="font-bold text-sm text-navy-500">{session.title}</h3>
              <p className="text-xs text-navy-500/50 mt-0.5">
                {isMentor ? `Scholar: ${session.scholar_name}` : `Mentor: ${session.mentor_name}`}
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-xs font-semibold text-navy-500">{fmtDate(session.start_time)}</p>
              <p className="text-xs text-navy-500/50">{fmtTime(session.start_time)} – {fmtTime(session.end_time)}</p>
              <p className="text-[10px] text-navy-500/30 mt-0.5">{session.duration_minutes} min</p>
            </div>
          </div>

          {session.agenda && (
            <p className="text-xs text-navy-500/60 bg-purple-50 rounded-lg px-3 py-2 mb-3">{session.agenda}</p>
          )}

          <div className="flex items-center gap-2 flex-wrap border-t border-purple-50 pt-3">
            {session.status === 'confirmed' && isJoinable && (
              <button
                type="button"
                disabled={joining}
                onClick={async () => {
                  setJoining(true);
                  try {
                    const { data } = await api.get(`/sessions/sessions/${session.id}/join/`);
                    window.open(data.url, '_blank', 'noopener,noreferrer');
                  } catch {
                    alert('Could not start the video call. Please try again in a moment.');
                  } finally {
                    setJoining(false);
                  }
                }}
                className="text-xs font-semibold bg-gradient-brand text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1 disabled:opacity-60">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.723v6.554a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                {joining ? 'Starting…' : 'Join video call'}
              </button>
            )}
            {isMentor && session.status === 'pending' && (
              <>
                <button onClick={() => onAction(session.id, 'confirm')}
                  className="text-xs font-semibold bg-green-500 text-white px-3 py-1.5 rounded-lg hover:bg-green-600 transition-colors">
                  Confirm
                </button>
                <button onClick={() => onAction(session.id, 'cancel')}
                  className="text-xs font-semibold bg-red-50 text-red-500 px-3 py-1.5 rounded-lg hover:bg-red-100 transition-colors">
                  Decline
                </button>
              </>
            )}
            {isMentor && session.status === 'confirmed' && !isUpcoming && (
              <button onClick={() => onAction(session.id, 'complete')}
                className="text-xs font-semibold bg-purple-50 text-purple-500 px-3 py-1.5 rounded-lg hover:bg-purple-100 transition-colors">
                Mark complete
              </button>
            )}
            {session.status !== 'pending' && session.status !== 'completed' && (
              <button onClick={() => onAction(session.id, 'cancel')}
                className="text-xs font-medium text-navy-500/60 px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
                Cancel session
              </button>
            )}
            {session.status === 'completed' && !alreadyFeedback && (
              <button onClick={() => setShowFeedback(true)}
                className="text-xs font-semibold text-pink-500 hover:underline ml-auto">
                Leave feedback
              </button>
            )}
            {session.status === 'completed' && alreadyFeedback && (
              <span className="text-xs text-navy-500/30 ml-auto flex items-center gap-1">
                <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                Feedback submitted
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Availability manager (mentor) ─────────────────────────────────────────────
function AvailabilityManager({ userId }: { userId: number }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'weekly' | 'oneoff'>('weekly');

  // Weekly schedule state
  const [selectedDays, setSelectedDays] = useState<Set<number>>(new Set());
  const [scheduleStart, setScheduleStart] = useState('09:00');
  const [scheduleEnd, setScheduleEnd]     = useState('10:00');
  const [weeksAhead, setWeeksAhead]       = useState(4);
  const [scheduleNotes, setScheduleNotes] = useState('');
  const [generating, setGenerating]       = useState(false);
  const [genError, setGenError]           = useState('');

  // One-off state
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime]     = useState('');
  const [notes, setNotes]         = useState('');

  const { data } = useQuery<PaginatedResponse<AvailabilitySlot>>({
    queryKey: ['slots', 'mine'],
    queryFn: () => api.get(`/sessions/slots/?mentor=${userId}&ordering=start_time&page_size=200`).then(r => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const toggleDay = (d: number) =>
    setSelectedDays(prev => {
      const next = new Set(prev);
      next.has(d) ? next.delete(d) : next.add(d);
      return next;
    });

  const generateWeekly = async () => {
    setGenError('');
    if (!selectedDays.size) return;
    setGenerating(true);
    try {
      const slots = buildWeeklySlots([...selectedDays], scheduleStart, scheduleEnd, weeksAhead);
      if (!slots.length) { setGenError('No future slots to create for those settings.'); return; }
      await Promise.all(slots.map(s =>
        api.post('/sessions/slots/', { start_time: s.start_time, end_time: s.end_time, notes: scheduleNotes })
      ));
      queryClient.invalidateQueries({ queryKey: ['slots', 'mine'] });
    } catch {
      setGenError('Something went wrong creating slots.');
    } finally {
      setGenerating(false);
    }
  };

  const addSlot = useMutation({
    mutationFn: () => api.post('/sessions/slots/', { start_time: startTime, end_time: endTime, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slots', 'mine'] });
      setStartTime(''); setEndTime(''); setNotes('');
    },
  });

  const deleteSlot = useMutation({
    mutationFn: (id: number) => api.delete(`/sessions/slots/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['slots', 'mine'] }),
  });

  const blockOutDate = async (dateKey: string, daySlots: AvailabilitySlot[]) => {
    const unbooked = daySlots.filter(s => !s.is_booked);
    if (!unbooked.length) return;
    await Promise.all(unbooked.map(s => api.delete(`/sessions/slots/${s.id}/`)));
    queryClient.invalidateQueries({ queryKey: ['slots', 'mine'] });
  };

  const allSlots = data?.results ?? [];
  const nowTs = Date.now();
  // Separate future and past-but-unbooked (expired) slots
  const activeSlots  = allSlots.filter(s => s.is_booked || new Date(s.start_time).getTime() > nowTs);
  const expiredSlots = allSlots.filter(s => !s.is_booked && new Date(s.start_time).getTime() <= nowTs);

  const grouped  = groupBy(activeSlots, s => localDateKey(s.start_time));
  const sortedDates = Object.keys(grouped).sort();

  const previewCount = selectedDays.size
    ? buildWeeklySlots([...selectedDays], scheduleStart, scheduleEnd, weeksAhead).length
    : 0;

  const inputCls = 'w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors';

  return (
    <div className="space-y-6">

      {/* ── Add availability ── */}
      <div className="bg-white rounded-2xl shadow-card p-5">

        {/* Mode toggle */}
        <div className="flex gap-1 p-1 bg-purple-50 rounded-xl mb-5">
          {(['weekly', 'oneoff'] as const).map(k => (
            <button key={k} onClick={() => setMode(k)}
              className={`flex-1 text-xs font-semibold py-2 px-3 rounded-lg transition-all ${mode === k ? 'bg-white text-navy-500 shadow-sm' : 'text-navy-500/50 hover:text-navy-500'}`}>
              {k === 'weekly' ? 'Weekly schedule' : 'One-off slot'}
            </button>
          ))}
        </div>

        {mode === 'weekly' ? (
          <div className="space-y-4">
            {/* Day picker */}
            <div>
              <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-2">Days available</label>
              <div className="flex gap-2 flex-wrap">
                {DAYS.map((day, i) => (
                  <button key={day} onClick={() => toggleDay(i)}
                    className={`w-11 h-11 rounded-xl text-xs font-bold transition-all ${
                      selectedDays.has(i)
                        ? 'bg-pink-500 text-white shadow-brand'
                        : 'bg-purple-50 text-navy-500/60 hover:bg-purple-100'
                    }`}>
                    {day}
                  </button>
                ))}
              </div>
            </div>

            {/* Time range */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-1">From</label>
                <input type="time" value={scheduleStart} onChange={e => setScheduleStart(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-1">To</label>
                <input type="time" value={scheduleEnd} onChange={e => setScheduleEnd(e.target.value)} className={inputCls} />
              </div>
            </div>

            {/* Weeks ahead selector */}
            <div>
              <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-2">Apply for next</label>
              <div className="flex gap-2">
                {[2, 4, 6, 8].map(w => (
                  <button key={w} onClick={() => setWeeksAhead(w)}
                    className={`flex-1 text-xs font-semibold py-2 rounded-lg border transition-all ${
                      weeksAhead === w
                        ? 'bg-pink-500 text-white border-pink-500'
                        : 'border-purple-200 text-navy-500/60 hover:border-purple-400'
                    }`}>
                    {w} weeks
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <input placeholder="Note for scholars e.g. 'video call preferred' (optional)"
              value={scheduleNotes} onChange={e => setScheduleNotes(e.target.value)} className={inputCls} />

            {genError && <p className="text-xs text-red-500">{genError}</p>}

            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-navy-500/40">
                {previewCount > 0
                  ? `Creates ${previewCount} slot${previewCount !== 1 ? 's' : ''}`
                  : 'Select days above'}
              </span>
              <button
                onClick={generateWeekly}
                disabled={!selectedDays.size || !scheduleStart || !scheduleEnd || generating || scheduleStart >= scheduleEnd}
                className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors">
                {generating ? 'Generating…' : 'Generate slots'}
              </button>
            </div>
          </div>
        ) : (
          /* One-off slot form */
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-1">Start</label>
                <input type="datetime-local" value={startTime} min={toLocalDT(new Date())} onChange={e => setStartTime(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-1">End</label>
                <input type="datetime-local" value={endTime} min={startTime || toLocalDT(new Date())} onChange={e => setEndTime(e.target.value)} className={inputCls} />
              </div>
            </div>
            <input placeholder="Note for scholars (optional)" value={notes} onChange={e => setNotes(e.target.value)} className={inputCls} />
            <div className="flex justify-end">
              <button onClick={() => addSlot.mutate()} disabled={!startTime || !endTime || addSlot.isPending}
                className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors">
                {addSlot.isPending ? 'Adding…' : '+ Add slot'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Upcoming slots grouped by date ── */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BrandStar />
          <h3 className="text-sm font-bold text-navy-500 uppercase tracking-widest">
            Upcoming availability
            {allSlots.length > 0 && (
              <span className="ml-2 text-navy-500/40 normal-case font-normal">({allSlots.length} slot{allSlots.length !== 1 ? 's' : ''})</span>
            )}
          </h3>
        </div>

        {/* Expired slot warning */}
        {expiredSlots.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 mb-4 flex items-start gap-3">
            <svg className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-xs font-semibold text-yellow-800">
                {expiredSlots.length} expired slot{expiredSlots.length !== 1 ? 's' : ''} — scholars cannot see these
              </p>
              <p className="text-xs text-yellow-700/70 mt-0.5">These slots are in the past. Please create new ones with future dates.</p>
            </div>
            <button
              onClick={async () => {
                await Promise.all(expiredSlots.map(s => api.delete(`/sessions/slots/${s.id}/`)));
                queryClient.invalidateQueries({ queryKey: ['slots', 'mine'] });
              }}
              className="text-[10px] font-semibold text-yellow-700 hover:text-yellow-900 border border-yellow-300 hover:border-yellow-500 px-2 py-1 rounded-lg transition-colors whitespace-nowrap flex-shrink-0">
              Remove all
            </button>
          </div>
        )}

        {!sortedDates.length ? (
          <div className="bg-white rounded-2xl shadow-card text-center py-12">
            <p className="text-sm text-navy-500/40">No slots set yet.</p>
            <p className="text-xs text-navy-500/30 mt-1">Use the weekly schedule above to get started.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedDates.map(dateKey => {
              const daySlots  = grouped[dateKey];
              const hasUnbooked = daySlots.some(s => !s.is_booked);
              // Parse as local date (append time to avoid UTC shift)
              const dateLabel = new Date(dateKey + 'T00:00:00').toLocaleDateString('en-GB', {
                weekday: 'long', day: 'numeric', month: 'short', year: 'numeric',
              });
              const bookedCount = daySlots.filter(s => s.is_booked).length;
              return (
                <div key={dateKey} className="bg-white rounded-2xl shadow-card overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-purple-50">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-navy-500">{dateLabel}</p>
                      {bookedCount > 0 && (
                        <span className="text-[10px] font-semibold bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded-full">
                          {bookedCount} booked
                        </span>
                      )}
                    </div>
                    {hasUnbooked && (
                      <button
                        onClick={() => blockOutDate(dateKey, daySlots)}
                        className="text-[10px] font-semibold text-red-400 hover:text-red-500 border border-red-200 hover:border-red-400 px-2 py-1 rounded-lg transition-colors whitespace-nowrap">
                        Block out day
                      </button>
                    )}
                  </div>
                  <div className="divide-y divide-purple-50">
                    {daySlots.map(slot => (
                      <div key={slot.id} className="flex items-center justify-between px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-navy-500 tabular-nums">
                            {fmtTime(slot.start_time)} – {fmtTime(slot.end_time)}
                          </span>
                          {slot.notes && (
                            <span className="text-xs text-navy-500/40 hidden sm:inline">{slot.notes}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${slot.is_booked ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                            {slot.is_booked ? 'Booked' : 'Open'}
                          </span>
                          {!slot.is_booked && (
                            <button
                              onClick={() => deleteSlot.mutate(slot.id)}
                              title="Remove slot"
                              className="text-navy-500/25 hover:text-red-500 transition-colors">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Book a session (scholar) ──────────────────────────────────────────────────
function BookingPanel({ currentUserId }: { currentUserId: number }) {
  const queryClient = useQueryClient();
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null);
  const [title, setTitle] = useState('Mentoring Session');
  const [agenda, setAgenda] = useState('');
  const [booked, setBooked] = useState(false);

  const { data: slots, isLoading } = useQuery<PaginatedResponse<AvailabilitySlot>>({
    queryKey: ['slots', 'available'],
    queryFn: () => api.get('/sessions/slots/').then(r => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const book = useMutation({
    mutationFn: () => api.post('/sessions/sessions/', {
      mentor: selectedSlot!.mentor,
      scholar: currentUserId,
      slot: selectedSlot!.id,
      title,
      agenda,
      start_time: selectedSlot!.start_time,
      end_time: selectedSlot!.end_time,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['slots', 'available'] });
      setBooked(true);
    },
  });

  if (booked) {
    return (
      <div className="text-center py-10 bg-white rounded-2xl shadow-card">
        <div className="w-12 h-12 rounded-2xl bg-gradient-brand-soft flex items-center justify-center shadow-brand mx-auto mb-4">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="font-bold text-navy-500 mb-1">Request sent!</h3>
        <p className="text-xs text-navy-500/50">Your mentor will confirm shortly.</p>
        <button onClick={() => { setBooked(false); setSelectedSlot(null); }}
          className="mt-4 text-xs font-semibold text-pink-500 hover:underline">Book another</button>
      </div>
    );
  }

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  const availableSlots = slots?.results?.filter(s => !s.is_booked) ?? [];

  return (
    <div className="space-y-4">
      {!selectedSlot ? (
        <>
          <p className="text-xs text-navy-500/50 mb-3">Select an available time slot from your mentor(s):</p>
          {!availableSlots.length ? (
            <div className="bg-white rounded-2xl shadow-card text-center py-12">
              <p className="text-sm text-navy-500/40">No available slots right now.</p>
              <p className="text-xs text-navy-500/30 mt-1">Your mentor will add times when they're free — check back soon.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {availableSlots.map(slot => (
                <button key={slot.id} onClick={() => setSelectedSlot(slot)}
                  className="w-full text-left bg-white rounded-xl shadow-card hover:shadow-brand transition-all p-4">
                  <p className="text-sm font-semibold text-navy-500">{slot.mentor_name}</p>
                  <p className="text-xs text-navy-500/50">{fmtDateTime(slot.start_time)} – {fmtTime(slot.end_time)}</p>
                  {slot.notes && <p className="text-xs text-navy-500/40 mt-0.5">{slot.notes}</p>}
                </button>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-2xl shadow-card p-5 space-y-4">
          <button onClick={() => setSelectedSlot(null)} className="text-xs text-pink-500 hover:underline flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" /></svg>
            Back
          </button>
          <div className="bg-purple-50 rounded-xl p-3 text-xs">
            <p className="font-semibold text-navy-500">{selectedSlot.mentor_name}</p>
            <p className="text-navy-500/60">{fmtDateTime(selectedSlot.start_time)} – {fmtTime(selectedSlot.end_time)}</p>
          </div>
          <div>
            <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-1">Session title</label>
            <input value={title} onChange={e => setTitle(e.target.value)}
              className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider block mb-1">Agenda / topics to discuss</label>
            <textarea rows={3} value={agenda} onChange={e => setAgenda(e.target.value)}
              className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none"
              placeholder="What would you like to discuss?" />
          </div>
          <button onClick={() => book.mutate()} disabled={!title || book.isPending}
            className="w-full text-sm font-semibold bg-pink-500 text-white py-2.5 rounded-xl hover:bg-pink-600 disabled:opacity-50 transition-colors shadow-brand">
            {book.isPending ? 'Sending request…' : 'Request this session'}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function SessionsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'upcoming' | 'past' | 'availability' | 'book'>('upcoming');

  const { data: sessions, isLoading } = useQuery<PaginatedResponse<MentoringSession>>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/sessions/sessions/').then(r => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const sessionAction = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) =>
      api.post(`/sessions/sessions/${id}/${action}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  });

  const now = new Date();
  const upcoming = sessions?.results?.filter(s => new Date(s.start_time) >= now && s.status !== 'cancelled') ?? [];
  const past     = sessions?.results?.filter(s => new Date(s.start_time) < now || s.status === 'completed' || s.status === 'cancelled') ?? [];

  const isMentor = user?.role === 'mentor';
  const tabs = [
    { key: 'upcoming',     label: `Upcoming (${upcoming.length})` },
    { key: 'past',         label: 'Past sessions' },
    ...(isMentor  ? [{ key: 'availability', label: 'My Availability' }] : []),
    ...(!isMentor ? [{ key: 'book',         label: '+ Book a session' }] : []),
  ] as { key: typeof tab; label: string }[];

  return (
    <div>
      {/* Header */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-8 mb-8 shadow-brand">
        <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full bg-white/5" />
        <div className="relative z-10">
          <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1">Scheduling</p>
          <h1 className="text-2xl font-extrabold">Sessions</h1>
          <p className="mt-1 text-white/60 text-sm">
            {isMentor ? 'Manage your mentoring sessions and availability.' : 'Book and manage your mentoring sessions.'}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white rounded-xl shadow-card p-1 mb-6 overflow-x-auto">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex-1 min-w-max text-xs font-semibold px-4 py-2 rounded-lg transition-all whitespace-nowrap ${tab === t.key ? 'bg-gradient-brand text-white shadow-brand' : 'text-navy-500/60 hover:text-navy-500'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>
      ) : (
        <>
          {tab === 'upcoming' && (
            <>
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Upcoming Sessions</h2></div>
              {!upcoming.length ? (
                <div className="text-center py-16 text-sm text-navy-500/40">
                  No upcoming sessions.
                  {!isMentor && <><button onClick={() => setTab('book')} className="text-pink-500 font-semibold hover:underline ml-1">Book one now.</button></>}
                </div>
              ) : (
                <div className="space-y-3">
                  {upcoming.map(s => <SessionCard key={s.id} session={s} currentUserId={user!.id}
                    onAction={(id, action) => sessionAction.mutate({ id, action })} />)}
                </div>
              )}
            </>
          )}

          {tab === 'past' && (
            <>
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Past Sessions</h2></div>
              {!past.length ? (
                <p className="text-center py-16 text-sm text-navy-500/40">No past sessions yet.</p>
              ) : (
                <div className="space-y-3">
                  {past.map(s => <SessionCard key={s.id} session={s} currentUserId={user!.id}
                    onAction={(id, action) => sessionAction.mutate({ id, action })} />)}
                </div>
              )}
            </>
          )}

          {tab === 'availability' && isMentor && user && (
            <>
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">My Availability</h2></div>
              <AvailabilityManager userId={user.id} />
            </>
          )}

          {tab === 'book' && !isMentor && user && (
            <>
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Book a Session</h2></div>
              <BookingPanel currentUserId={user.id} />
            </>
          )}
        </>
      )}
    </div>
  );
}
