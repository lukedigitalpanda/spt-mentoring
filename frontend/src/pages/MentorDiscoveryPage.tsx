import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

interface MentorCard {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  engineering_discipline: string;
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
    skills: string[];
  };
}

const DISCIPLINES = [
  'Mechanical', 'Electrical', 'Civil', 'Chemical', 'Software',
  'Aerospace', 'Biomedical', 'Environmental', 'Materials', 'Other',
];

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
        <span className="text-xs text-navy-DEFAULT/60 ml-1">{value.toFixed(1)}</span>
      )}
    </div>
  );
}

function MentorCard({ mentor, onBook }: { mentor: MentorCard; onBook: (m: MentorCard) => void }) {
  const initials = `${mentor.first_name[0] ?? ''}${mentor.last_name[0] ?? ''}`;

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
              <h3 className="font-bold text-navy-DEFAULT text-base leading-tight">{mentor.full_name}</h3>
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
              <p className="text-xs text-purple-DEFAULT font-medium mt-0.5 truncate">
                {mentor.mentor_profile.job_title}
                {mentor.mentor_profile.company ? ` · ${mentor.mentor_profile.company}` : ''}
              </p>
            )}

            <div className="flex items-center gap-3 mt-1.5 flex-wrap">
              <StarRating value={mentor.avg_rating} />
              {mentor.session_count > 0 && (
                <span className="text-xs text-navy-DEFAULT/50">
                  {mentor.session_count} session{mentor.session_count !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Discipline pill */}
        {mentor.engineering_discipline && (
          <div className="mt-3">
            <span className="inline-block text-[11px] font-semibold bg-purple-50 text-purple-700 px-2.5 py-1 rounded-full">
              {mentor.engineering_discipline}
            </span>
            {mentor.location && (
              <span className="inline-block text-[11px] text-navy-DEFAULT/50 ml-2">
                📍 {mentor.location}
              </span>
            )}
          </div>
        )}

        {/* Bio */}
        {mentor.bio && (
          <p className="mt-3 text-xs text-navy-DEFAULT/70 line-clamp-2 leading-relaxed">
            {mentor.bio}
          </p>
        )}

        {/* Skills */}
        {mentor.mentor_profile?.skills?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {mentor.mentor_profile.skills.slice(0, 4).map(skill => (
              <span key={skill} className="text-[10px] bg-gray-50 border border-gray-200 text-navy-DEFAULT/70 px-2 py-0.5 rounded-full">
                {skill}
              </span>
            ))}
            {mentor.mentor_profile.skills.length > 4 && (
              <span className="text-[10px] text-navy-DEFAULT/40">+{mentor.mentor_profile.skills.length - 4} more</span>
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
          <h3 className="font-bold text-navy-DEFAULT text-lg">Request a Session</h3>
          <button onClick={onClose} className="text-navy-DEFAULT/40 hover:text-navy-DEFAULT">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex items-center gap-3 mb-5 p-3 bg-purple-50 rounded-xl">
          <div className="w-10 h-10 rounded-full bg-gradient-brand-soft flex items-center justify-center text-white font-bold text-sm">
            {mentor.first_name[0]}{mentor.last_name[0]}
          </div>
          <div>
            <p className="font-semibold text-navy-DEFAULT text-sm">{mentor.full_name}</p>
            {mentor.mentor_profile?.job_title && (
              <p className="text-xs text-purple-DEFAULT">{mentor.mentor_profile.job_title}</p>
            )}
          </div>
        </div>

        <p className="text-sm text-navy-DEFAULT/70 mb-5">
          Head to the Sessions page to view {mentor.first_name}'s available time slots and book a session.
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
            className="px-4 py-2.5 rounded-xl border border-gray-200 text-navy-DEFAULT/60 text-sm font-medium hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MentorDiscoveryPage() {
  const [discipline, setDiscipline] = useState('');
  const [search, setSearch] = useState('');
  const [availableOnly, setAvailableOnly] = useState(false);
  const [bookMentor, setBookMentor] = useState<MentorCard | null>(null);

  const params = new URLSearchParams();
  if (discipline) params.set('discipline', discipline);
  if (availableOnly) params.set('available', '1');

  const { data: mentors = [], isLoading } = useQuery<MentorCard[]>({
    queryKey: ['mentors', discipline, availableOnly],
    queryFn: () => api.get(`/users/mentors/?${params}`).then(r => r.data),
  });

  const filtered = mentors.filter(m => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      m.full_name.toLowerCase().includes(q) ||
      m.engineering_discipline?.toLowerCase().includes(q) ||
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
            <h1 className="text-2xl font-bold text-navy-DEFAULT">Find a Mentor</h1>
            <p className="text-sm text-navy-DEFAULT/60">Discover engineers who can guide your journey</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-card border border-purple-100 p-4 mb-6 flex flex-wrap gap-3 items-center">
        <div className="flex-1 min-w-[180px]">
          <input
            type="text"
            placeholder="Search by name, discipline, company..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-purple-DEFAULT"
          />
        </div>

        <select
          value={discipline}
          onChange={e => setDiscipline(e.target.value)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-purple-DEFAULT"
        >
          <option value="">All disciplines</option>
          {DISCIPLINES.map(d => <option key={d} value={d}>{d}</option>)}
        </select>

        <label className="flex items-center gap-2 text-sm font-medium text-navy-DEFAULT cursor-pointer select-none">
          <input
            type="checkbox"
            checked={availableOnly}
            onChange={e => setAvailableOnly(e.target.checked)}
            className="rounded border-gray-300 text-purple-DEFAULT focus:ring-purple-DEFAULT"
          />
          Available now
        </label>

        <span className="text-xs text-navy-DEFAULT/50 ml-auto">
          {filtered.length} mentor{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 border-4 border-purple-200 border-t-purple-DEFAULT rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-navy-DEFAULT/40">
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
