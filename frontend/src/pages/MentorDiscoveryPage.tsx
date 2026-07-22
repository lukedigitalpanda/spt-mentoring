import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import { userHasRole } from '../utils/roles';

interface WaitingListEntry {
  id: number;
  scholar: number;
  engineering_discipline: string;
  requested_at: string;
  is_matched: boolean;
}

interface MentorCard {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  engineering_discipline: string;
  engineering_disciplines: string[];
  location: string;
  bio: string;
  avg_rating: number;
  session_count: number;
  is_verified: boolean;
  mentor_profile?: {
    company: string;
    job_title: string;
    years_experience: number;
    max_scholars: number;
    specialisms: string[];
  };
}

const DISCIPLINES = [
  'Aerospace', 'Astronautics', 'Biomedical', 'Chemical', 'Civil', 'Electrical',
  'Environmental', 'Materials', 'Mechanical', 'Software', 'Structural', 'Other',
];

// Derive avatar initials defensively. The list API may omit first_name/last_name,
// so fall back to full_name so the card never crashes on undefined access.
function getInitials(mentor: MentorCard): string {
  const first = mentor.first_name?.trim();
  const last = mentor.last_name?.trim();
  if (first || last) {
    return `${first?.[0] ?? ''}${last?.[0] ?? ''}`.toUpperCase();
  }
  const parts = (mentor.full_name ?? '').trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map(p => p[0]).join('').toUpperCase();
}

// First name for friendly copy, falling back to the first word of full_name.
function firstNameOf(mentor: MentorCard): string {
  return (mentor.first_name?.trim() || (mentor.full_name ?? '').trim().split(/\s+/)[0] || 'this mentor');
}

function StarRating({ value, size = 'sm' }: { value: number; size?: 'sm' | 'md' }) {
  const sz = size === 'md' ? 'w-5 h-5' : 'w-3.5 h-3.5';
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(s => (
        <svg key={s} className={`${sz} ${s <= Math.round(value) ? 'text-yellow-400' : 'text-gray-200'}`}
          fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      {value > 0 && (
        <span className="text-xs text-navy-500/60 ml-1">{value.toFixed(1)}</span>
      )}
    </div>
  );
}

function MentorCard({ mentor, onBook }: { mentor: MentorCard; onBook: (m: MentorCard) => void }) {
  const initials = getInitials(mentor);
  const [expandedBios, setExpandedBios] = useState<Set<number>>(new Set());
  const toggleBio = (id: number) => {
    setExpandedBios(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <div className="bg-white rounded-2xl shadow-card border border-purple-100 overflow-hidden hover:shadow-brand transition-all group">
      {/* Card top band */}
      <div className="h-2 bg-gradient-brand" />

      <div className="p-5">
        {/* Avatar + name */}
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-full bg-gradient-brand-soft flex items-center justify-center text-white font-bold text-lg shadow-brand flex-shrink-0">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-navy-500 text-base leading-tight break-words">{mentor.full_name}</h3>
              {mentor.is_verified && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-green-50 text-green-700 px-1.5 py-0.5 rounded-full">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Verified
                </span>
              )}
            </div>

            {mentor.mentor_profile?.job_title && (
              <p className="text-xs text-purple-500 font-medium mt-0.5 truncate">
                {mentor.mentor_profile.job_title}
                {mentor.mentor_profile.company ? ` · ${mentor.mentor_profile.company}` : ''}
              </p>
            )}

            <div className="flex items-center gap-3 mt-1.5 flex-wrap">
              <StarRating value={mentor.avg_rating} />
              {mentor.session_count > 0 && (
                <span className="text-xs text-navy-500/50">
                  {mentor.session_count} session{mentor.session_count !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Discipline pills */}
        {((mentor.engineering_disciplines?.length ?? 0) > 0 || mentor.engineering_discipline) && (
          <div className="mt-3 flex flex-wrap gap-1 items-center">
            {(mentor.engineering_disciplines?.length > 0
              ? mentor.engineering_disciplines
              : [mentor.engineering_discipline]
            ).map(d => (
              <span key={d} className="inline-block text-[11px] font-semibold bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full">
                {d}
              </span>
            ))}
            {mentor.location && (
              <span className="inline-block text-[11px] text-navy-500/50 ml-1">
                📍 {mentor.location}
              </span>
            )}
          </div>
        )}

        {/* Bio */}
        {mentor.bio && (
          <>
            <p className={`mt-3 text-xs text-navy-500/70 leading-relaxed whitespace-pre-wrap break-words ${expandedBios.has(mentor.id) ? '' : 'line-clamp-2'}`}>
              {mentor.bio}
            </p>
            {mentor.bio.length > 120 && (
              <button onClick={() => toggleBio(mentor.id)} className="mt-1 text-xs font-medium text-pink-500 hover:underline">
                {expandedBios.has(mentor.id) ? 'Show less' : 'Read more'}
              </button>
            )}
          </>
        )}

        {/* Skills */}
        {(mentor.mentor_profile?.specialisms?.length ?? 0) > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {mentor.mentor_profile!.specialisms.slice(0, 4).map(skill => (
              <span key={skill} className="text-[10px] bg-gray-50 border border-gray-200 text-navy-500/70 px-2 py-0.5 rounded-full">
                {skill}
              </span>
            ))}
            {mentor.mentor_profile!.specialisms.length > 4 && (
              <span className="text-[10px] text-navy-500/40">+{mentor.mentor_profile!.specialisms.length - 4} more</span>
            )}
          </div>
        )}

        {/* CTA */}
        <button
          onClick={() => onBook(mentor)}
          className="mt-4 w-full bg-gradient-brand text-white text-sm font-semibold py-2.5 rounded-xl hover:opacity-90 transition-opacity shadow-brand"
        >
          Request a Session
        </button>
      </div>
    </div>
  );
}

function BookRequestModal({ mentor, onClose }: { mentor: MentorCard; onClose: () => void }) {
  const navigate = useNavigate();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-navy-500 text-lg">Request a Session</h3>
          <button onClick={onClose} className="text-navy-500/40 hover:text-navy-500">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex items-center gap-3 mb-5 p-3 bg-purple-50 rounded-xl">
          <div className="w-10 h-10 rounded-full bg-gradient-brand-soft flex items-center justify-center text-white font-bold text-sm">
            {getInitials(mentor)}
          </div>
          <div>
            <p className="font-semibold text-navy-500 text-sm">{mentor.full_name}</p>
            {mentor.mentor_profile?.job_title && (
              <p className="text-xs text-purple-500">{mentor.mentor_profile.job_title}</p>
            )}
          </div>
        </div>

        <p className="text-sm text-navy-500/70 mb-5">
          Head to the Sessions page to view {firstNameOf(mentor)}'s available time slots and book a session.
        </p>

        <div className="flex gap-3">
          <button
            onClick={() => { navigate('/sessions'); onClose(); }}
            className="flex-1 bg-gradient-brand text-white font-semibold py-2.5 rounded-xl hover:opacity-90 transition-opacity"
          >
            Go to Sessions
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-gray-200 text-navy-500/60 text-sm font-medium hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MentorDiscoveryPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [discipline, setDiscipline] = useState('');
  const [search, setSearch] = useState('');
  const [availableOnly, setAvailableOnly] = useState(false);
  const [bookMentor, setBookMentor] = useState<MentorCard | null>(null);

  const params = new URLSearchParams();
  if (discipline) params.set('discipline', discipline);
  if (availableOnly) params.set('available', '1');

  const { data: mentors = [], isLoading, isError, refetch } = useQuery<MentorCard[]>({
    queryKey: ['mentors', discipline, availableOnly],
    // Guard against a non-array payload so a malformed response can never crash the grid.
    queryFn: () => api.get(`/users/mentors/?${params}`).then(r => (Array.isArray(r.data) ? r.data : [])),
  });

  // Waiting list (MATCH-02): unmatched scholars can ask to be matched by staff.
  const isUnmatchedScholar = userHasRole(user, 'scholar') && !user?.has_mentor;
  const { data: waitingList } = useQuery<{ results: WaitingListEntry[] }>({
    queryKey: ['waiting-list'],
    queryFn: () => api.get('/users/waiting-list/').then(r => r.data),
    enabled: isUnmatchedScholar,
  });
  const waitingEntry = waitingList?.results?.find(e => !e.is_matched);
  const joinWaitingList = useMutation({
    mutationFn: () =>
      api.post('/users/waiting-list/', { engineering_discipline: discipline || '' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['waiting-list'] }),
  });

  const filtered = mentors.filter(m => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      m.full_name.toLowerCase().includes(q) ||
      m.engineering_discipline?.toLowerCase().includes(q) ||
      m.engineering_disciplines?.some(d => d.toLowerCase().includes(q)) ||
      m.mentor_profile?.job_title?.toLowerCase().includes(q) ||
      m.mentor_profile?.company?.toLowerCase().includes(q) ||
      m.bio?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-brand-soft flex items-center justify-center shadow-brand">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-navy-500">Find a Mentor</h1>
            <p className="text-sm text-navy-500/60">Discover engineers who can guide your journey</p>
          </div>
        </div>
      </div>

      {/* Waiting list banner — unmatched scholars only */}
      {isUnmatchedScholar && (
        waitingEntry ? (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-4 mb-6 flex items-start gap-3">
            <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-semibold text-green-800">You're on the mentor waiting list</p>
              <p className="text-xs text-green-700 mt-0.5">
                Requested on {new Date(waitingEntry.requested_at).toLocaleDateString('en-GB')}.
                The Smallpeice team will be in touch when a suitable mentor is available.
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-purple-50 border border-purple-200 rounded-2xl p-4 mb-6 flex flex-wrap items-center gap-3 justify-between">
            <div>
              <p className="text-sm font-semibold text-navy-500">Can't find the right mentor?</p>
              <p className="text-xs text-navy-500/60 mt-0.5">
                Join the waiting list and the Smallpeice team will match you with a suitable mentor.
              </p>
              {joinWaitingList.isError && (
                <p className="text-xs text-red-500 mt-1">Could not join the waiting list. Please try again.</p>
              )}
            </div>
            <button
              onClick={() => joinWaitingList.mutate()}
              disabled={joinWaitingList.isPending}
              className="bg-gradient-brand text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:opacity-90 disabled:opacity-50 transition-opacity shadow-brand"
            >
              {joinWaitingList.isPending ? 'Joining…' : 'Join Waiting List'}
            </button>
          </div>
        )
      )}

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-card border border-purple-100 p-4 mb-6 flex flex-wrap gap-3 items-center">
        <div className="flex-1 min-w-[180px]">
          <input
            type="text"
            placeholder="Search by name, discipline, company..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
          />
        </div>

        <select
          value={discipline}
          onChange={e => setDiscipline(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="">All disciplines</option>
          {DISCIPLINES.map(d => <option key={d} value={d}>{d}</option>)}
        </select>

        <label className="flex items-center gap-2 text-sm font-medium text-navy-500 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={availableOnly}
            onChange={e => setAvailableOnly(e.target.checked)}
            className="rounded border-gray-300 text-purple-500 focus:ring-purple-500"
          />
          Available now
        </label>

        <span className="text-xs text-navy-500/50 ml-auto">
          {filtered.length} mentor{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 border-4 border-purple-200 border-t-purple-500 rounded-full animate-spin" />
        </div>
      ) : isError ? (
        <div className="text-center py-20 text-navy-500/60">
          <svg className="w-12 h-12 mx-auto mb-3 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="font-medium">We could not load mentors right now</p>
          <p className="text-sm mt-1 mb-4">Please check your connection and try again.</p>
          <button
            onClick={() => refetch()}
            className="bg-gradient-brand text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:opacity-90 transition-opacity shadow-brand"
          >
            Try again
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-navy-500/40">
          <svg className="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <p className="font-medium">No mentors found</p>
          <p className="text-sm mt-1">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map(m => (
            <MentorCard key={m.id} mentor={m} onBook={setBookMentor} />
          ))}
        </div>
      )}

      {bookMentor && (
        <BookRequestModal mentor={bookMentor} onClose={() => setBookMentor(null)} />
      )}
    </div>
  );
}
