import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { MentoringSession, AvailabilitySlot, SessionFeedback, PaginatedResponse } from '../types';

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
      <h3 className="text-base font-bold text-navy-DEFAULT">Rate your session</h3>

      {/* Star rating */}
      <div>
        <p className="text-xs font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-2">Overall rating</p>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map(n => (
            <button key={n} type="button" onClick={() => setRating(n)}
              className={`w-10 h-10 rounded-xl text-lg transition-all ${rating >= n ? 'text-yellow-400' : 'text-gray-200'}`}>
              ★
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-1">What went well?</p>
        <textarea rows={2} value={highlights} onChange={e => setHighlights(e.target.value)}
          className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 resize-none"
          placeholder="Highlights from the session…" />
      </div>
      <div>
        <p className="text-xs font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-1">What could improve?</p>
        <textarea rows={2} value={improvements} onChange={e => setImprovements(e.target.value)}
          className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 resize-none"
          placeholder="Suggestions for next time…" />
      </div>
      <div>
        <p className="text-xs font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-2">Would you recommend this mentor?</p>
        <div className="flex gap-2">
          {[true, false].map(v => (
            <button key={String(v)} type="button" onClick={() => setWouldRecommend(v)}
              className={`text-xs font-semibold px-4 py-1.5 rounded-lg border transition-all ${wouldRecommend === v ? 'bg-pink-DEFAULT text-white border-pink-DEFAULT' : 'border-purple-100 text-navy-DEFAULT/60'}`}>
              {v ? 'Yes' : 'No'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2 justify-end pt-2">
        <button onClick={onDone} className="text-xs text-navy-DEFAULT/50 px-3 py-1.5 rounded-lg hover:bg-gray-50">Cancel</button>
        <button
          onClick={() => submit.mutate()}
          disabled={rating === 0 || submit.isPending}
          className="text-xs font-semibold bg-pink-DEFAULT text-white px-4 py-1.5 rounded-lg hover:bg-pink-600 disabled:opacity-50 transition-colors">
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
              <h3 className="font-bold text-sm text-navy-DEFAULT">{session.title}</h3>
              <p className="text-xs text-navy-DEFAULT/50 mt-0.5">
                {isMentor ? `Scholar: ${session.scholar_name}` : `Mentor: ${session.mentor_name}`}
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-xs font-semibold text-navy-DEFAULT">{fmtDate(session.start_time)}</p>
              <p className="text-xs text-navy-DEFAULT/50">{fmtTime(session.start_time)} – {fmtTime(session.end_time)}</p>
              <p className="text-[10px] text-navy-DEFAULT/30 mt-0.5">{session.duration_minutes} min</p>
            </div>
          </div>

          {session.agenda && (
            <p className="text-xs text-navy-DEFAULT/60 bg-purple-50 rounded-lg px-3 py-2 mb-3">{session.agenda}</p>
          )}

          <div className="flex items-center gap-2 flex-wrap border-t border-purple-50 pt-3">
            {/* Join meeting button for confirmed upcoming sessions */}
            {session.status === 'confirmed' && isUpcoming && session.meeting_url && (
              <a href={session.meeting_url} target="_blank" rel="noopener noreferrer"
                className="text-xs font-semibold bg-gradient-brand text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.723v6.554a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Join Jitsi call
              </a>
            )}

            {/* Mentor actions */}
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
                className="text-xs font-semibold bg-purple-50 text-purple-DEFAULT px-3 py-1.5 rounded-lg hover:bg-purple-100 transition-colors">
                Mark complete
              </button>
            )}
            {session.status !== 'pending' && session.status !== 'completed' && (
              <button onClick={() => onAction(session.id, 'cancel')}
                className="text-xs text-navy-DEFAULT/40 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors">
                Cancel
              </button>
            )}

            {/* Feedback */}
            {session.status === 'completed' && !alreadyFeedback && (
              <button onClick={() => setShowFeedback(true)}
                className="text-xs font-semibold text-pink-DEFAULT hover:underline ml-auto">
                Leave feedback
              </button>
            )}
            {session.status === 'completed' && alreadyFeedback && (
              <span className="text-xs text-navy-DEFAULT/30 ml-auto flex items-center gap-1">
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
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [notes, setNotes] = useState('');

  const { data } = useQuery<PaginatedResponse<AvailabilitySlot>>({
    queryKey: ['slots', 'mine'],
    queryFn: () => api.get(`/sessions/slots/?mentor=${userId}`).then(r => r.data),
  });

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

  return (
    <div className="space-y-4">
      {/* Add slot form */}
      <div className="bg-white rounded-2xl shadow-card p-5">
        <h3 className="text-sm font-bold text-navy-DEFAULT mb-3">Add availability slot</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider block mb-1">Start</label>
            <input type="datetime-local" value={startTime} onChange={e => setStartTime(e.target.value)}
              className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider block mb-1">End</label>
            <input type="datetime-local" value={endTime} onChange={e => setEndTime(e.target.value)}
              className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30" />
          </div>
          <div className="sm:col-span-2">
            <input placeholder="Optional note for scholars (e.g. video or phone)" value={notes} onChange={e => setNotes(e.target.value)}
              className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30" />
          </div>
        </div>
        <div className="flex justify-end mt-3">
          <button onClick={() => addSlot.mutate()} disabled={!startTime || !endTime || addSlot.isPending}
            className="text-xs font-semibold bg-pink-DEFAULT text-white px-4 py-1.5 rounded-lg hover:bg-pink-600 disabled:opacity-50 transition-colors">
            {addSlot.isPending ? 'Adding…' : '+ Add slot'}
          </button>
        </div>
      </div>

      {/* Existing slots */}
      {data?.results?.length ? (
        <div className="space-y-2">
          {data.results.map(slot => (
            <div key={slot.id} className="bg-white rounded-xl shadow-card p-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-navy-DEFAULT">{fmtDate(slot.start_time)}</p>
                <p className="text-xs text-navy-DEFAULT/50">{fmtTime(slot.start_time)} – {fmtTime(slot.end_time)}</p>
                {slot.notes && <p className="text-xs text-navy-DEFAULT/40 mt-0.5">{slot.notes}</p>}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${slot.is_booked ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
                  {slot.is_booked ? 'Booked' : 'Open'}
                </span>
                {!slot.is_booked && (
                  <button onClick={() => deleteSlot.mutate(slot.id)} className="text-navy-DEFAULT/30 hover:text-red-500 transition-colors">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-navy-DEFAULT/40 text-center py-6">No availability slots yet.</p>
      )}
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
    queryFn: () => api.get('/sessions/slots/?is_booked=false').then(r => r.data),
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
        <h3 className="font-bold text-navy-DEFAULT mb-1">Request sent!</h3>
        <p className="text-xs text-navy-DEFAULT/50">Your mentor will confirm shortly.</p>
        <button onClick={() => { setBooked(false); setSelectedSlot(null); }}
          className="mt-4 text-xs font-semibold text-pink-DEFAULT hover:underline">Book another</button>
      </div>
    );
  }

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-4">
      {!selectedSlot ? (
        <>
          <p className="text-xs text-navy-DEFAULT/50 mb-3">Select an available time slot from your mentor(s):</p>
          {!slots?.results?.length ? (
            <p className="text-sm text-navy-DEFAULT/40 text-center py-8">No available slots right now. Your mentor will add times when they're free.</p>
          ) : (
            <div className="space-y-2">
              {slots.results.map(slot => (
                <button key={slot.id} onClick={() => setSelectedSlot(slot)}
                  className="w-full text-left bg-white rounded-xl shadow-card hover:shadow-brand transition-all p-4">
                  <p className="text-sm font-semibold text-navy-DEFAULT">{slot.mentor_name}</p>
                  <p className="text-xs text-navy-DEFAULT/50">{fmtDateTime(slot.start_time)} – {fmtTime(slot.end_time)}</p>
                  {slot.notes && <p className="text-xs text-navy-DEFAULT/40 mt-0.5">{slot.notes}</p>}
                </button>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="bg-white rounded-2xl shadow-card p-5 space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <button onClick={() => setSelectedSlot(null)} className="text-xs text-pink-DEFAULT hover:underline flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" /></svg>
              Back
            </button>
          </div>
          <div className="bg-purple-50 rounded-xl p-3 text-xs">
            <p className="font-semibold text-navy-DEFAULT">{selectedSlot.mentor_name}</p>
            <p className="text-navy-DEFAULT/60">{fmtDateTime(selectedSlot.start_time)} – {fmtTime(selectedSlot.end_time)}</p>
          </div>
          <div>
            <label className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider block mb-1">Session title</label>
            <input value={title} onChange={e => setTitle(e.target.value)}
              className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider block mb-1">Agenda / topics to discuss</label>
            <textarea rows={3} value={agenda} onChange={e => setAgenda(e.target.value)}
              className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 resize-none"
              placeholder="What would you like to discuss?" />
          </div>
          <button onClick={() => book.mutate()} disabled={!title || book.isPending}
            className="w-full text-sm font-semibold bg-pink-DEFAULT text-white py-2.5 rounded-xl hover:bg-pink-600 disabled:opacity-50 transition-colors shadow-brand">
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
  });

  const sessionAction = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) =>
      api.post(`/sessions/sessions/${id}/${action}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  });

  const now = new Date();
  const upcoming = sessions?.results?.filter(s => new Date(s.start_time) >= now && s.status !== 'cancelled') ?? [];
  const past = sessions?.results?.filter(s => new Date(s.start_time) < now || s.status === 'completed' || s.status === 'cancelled') ?? [];

  const isMentor = user?.role === 'mentor';
  const tabs = [
    { key: 'upcoming', label: `Upcoming (${upcoming.length})` },
    { key: 'past', label: 'Past sessions' },
    ...(isMentor ? [{ key: 'availability', label: 'My Availability' }] : []),
    ...(!isMentor ? [{ key: 'book', label: '+ Book a session' }] : []),
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
            className={`flex-1 min-w-max text-xs font-semibold px-4 py-2 rounded-lg transition-all whitespace-nowrap ${tab === t.key ? 'bg-gradient-brand text-white shadow-brand' : 'text-navy-DEFAULT/60 hover:text-navy-DEFAULT'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" /></div>
      ) : (
        <>
          {tab === 'upcoming' && (
            <>
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Upcoming Sessions</h2></div>
              {!upcoming.length ? (
                <div className="text-center py-16 text-sm text-navy-DEFAULT/40">
                  No upcoming sessions.
                  {!isMentor && <> <button onClick={() => setTab('book')} className="text-pink-DEFAULT font-semibold hover:underline ml-1">Book one now.</button></>}
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
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Past Sessions</h2></div>
              {!past.length ? (
                <p className="text-center py-16 text-sm text-navy-DEFAULT/40">No past sessions yet.</p>
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
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">My Availability</h2></div>
              <AvailabilityManager userId={user.id} />
            </>
          )}

          {tab === 'book' && !isMentor && user && (
            <>
              <div className="flex items-center gap-2 mb-4"><BrandStar /><h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Book a Session</h2></div>
              <BookingPanel currentUserId={user.id} />
            </>
          )}
        </>
      )}
    </div>
  );
}
