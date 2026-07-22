import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import { usePushNotifications } from '../hooks/usePushNotifications';
import type { User } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

const roleBadgeStyle: Record<string, string> = {
  scholar:  'bg-purple-100 text-purple-700',
  mentor:   'bg-navy-100  text-navy-700',
  sponsor:  'bg-orange-100 text-orange-700',
  alumni:   'bg-pink-100  text-pink-700',
  admin:    'bg-gradient-brand-soft text-white',
};

interface FieldProps {
  label: string;
  value?: string | number | null;
  placeholder?: string;
  editing: boolean;
  onChange?: (v: string) => void;
  type?: string;
  multiline?: boolean;
}

function Field({ label, value, placeholder, editing, onChange, type = 'text', multiline }: FieldProps) {
  const display = value != null && value !== '' ? String(value) : '—';
  return (
    <div>
      <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-1">{label}</p>
      {editing ? (
        multiline ? (
          <textarea
            className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none"
            rows={3}
            placeholder={placeholder}
            value={String(value ?? '')}
            onChange={e => onChange?.(e.target.value)}
          />
        ) : (
          <input
            type={type}
            className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors"
            placeholder={placeholder}
            value={String(value ?? '')}
            onChange={e => onChange?.(e.target.value)}
          />
        )
      ) : (
        <p className="text-sm text-navy-500">{display}</p>
      )}
    </div>
  );
}

// TC-13: Standard engineering disciplines list
const ENGINEERING_DISCIPLINES = [
  'Aerospace', 'Astronautics', 'Biomedical', 'Chemical', 'Civil', 'Electrical',
  'Environmental', 'Materials', 'Mechanical', 'Software', 'Structural', 'Other',
];

// ── Engineering disciplines multi-select ─────────────────────────────────────
function EngineeringDisciplinesEditor({
  disciplines,
  editing,
  onChange,
}: {
  disciplines: string[];
  editing: boolean;
  onChange: (v: string[]) => void;
}) {
  const toggle = (d: string) => {
    if (disciplines.includes(d)) onChange(disciplines.filter(x => x !== d));
    else onChange([...disciplines, d]);
  };

  return (
    <div className="sm:col-span-2">
      <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">
        Engineering Disciplines
      </p>
      {editing ? (
        <div className="flex flex-wrap gap-2">
          {ENGINEERING_DISCIPLINES.map(d => (
            <button
              key={d}
              type="button"
              onClick={() => toggle(d)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-full border transition-all ${
                disciplines.includes(d)
                  ? 'bg-purple-500 text-white border-purple-500'
                  : 'bg-white text-navy-500/60 border-purple-200 hover:border-purple-400'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {disciplines.length ? disciplines.map(d => (
            <span key={d} className="inline-flex items-center bg-purple-100 text-purple-700 text-xs font-semibold px-3 py-1 rounded-full">
              {d}
            </span>
          )) : <span className="text-sm text-navy-500/40">—</span>}
        </div>
      )}
    </div>
  );
}

// ── Specialism tag editor ─────────────────────────────────────────────────────
function SpecialismsEditor({
  specialisms,
  editing,
  onChange,
  label = 'Specialisms',
  maxItems,
}: {
  specialisms: string[];
  editing: boolean;
  onChange: (v: string[]) => void;
  label?: string;
  maxItems?: number;
}) {
  const [input, setInput] = useState('');

  const add = () => {
    const v = input.trim();
    if (v && !specialisms.includes(v) && (!maxItems || specialisms.length < maxItems)) onChange([...specialisms, v]);
    setInput('');
  };

  return (
    <div className="sm:col-span-2">
      <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">
        {label}{maxItems ? <span className="normal-case font-normal opacity-60 ml-1">(max {maxItems})</span> : null}
      </p>
      <div className="flex flex-wrap gap-2 mb-2">
        {specialisms.length ? specialisms.map(s => (
          <span key={s} className="inline-flex items-center gap-1 bg-purple-100 text-purple-700 text-xs font-semibold px-3 py-1 rounded-full">
            {s}
            {editing && (
              <button
                type="button"
                onClick={() => onChange(specialisms.filter(x => x !== s))}
                className="ml-0.5 text-purple-400 hover:text-red-500 leading-none"
                aria-label={`Remove ${s}`}
              >
                ×
              </button>
            )}
          </span>
        )) : (
          <span className="text-sm text-navy-500/40">—</span>
        )}
      </div>
      {editing && (
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors"
            placeholder={`Add ${label.toLowerCase()} and press Enter or Add…`}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
          />
          <button
            type="button"
            onClick={add}
            className="text-xs font-semibold bg-pink-500 hover:bg-pink-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
}

// ── Cohort badges (used by both mentor and scholar sections) ──────────────────
function CohortBadges({ user }: { user: User }) {
  if (!user.cohorts?.length) return null;
  return (
    <div className="sm:col-span-2">
      <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Cohort{user.cohorts.length > 1 ? 's' : ''}</p>
      <div className="flex flex-wrap gap-2">
        {user.cohorts.map(c => (
          <span
            key={c.cohort_id}
            className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold ${c.is_active ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'}`}
          >
            {c.programme_name} — {c.cohort_name}
            <span className="text-[10px] opacity-60">({c.cohort_year})</span>
            {!c.is_active && <span className="text-[10px] ml-1 opacity-50">inactive</span>}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Mentor profile section ────────────────────────────────────────────────────
function MentorSection({
  user,
  editing,
  onChange,
  onSpecialismsChange,
}: {
  user: User;
  editing: boolean;
  onChange: (field: string, v: string) => void;
  onSpecialismsChange: (v: string[]) => void;
}) {
  const mp = user.mentor_profile;
  if (!mp) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Mentor Profile</h2>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="Company" value={mp.company} placeholder="Your employer" editing={editing} onChange={v => onChange('mentor_profile.company', v)} />
        <Field label="Job Title" value={mp.job_title} placeholder="Your role" editing={editing} onChange={v => onChange('mentor_profile.job_title', v)} />
        <Field label="Years Experience" value={mp.years_experience} type="number" editing={editing} onChange={v => onChange('mentor_profile.years_experience', v)} />
        <Field label="Max scholars" value={mp.max_scholars} type="number" editing={editing} onChange={v => onChange('mentor_profile.max_scholars', v)} />
        <div className="sm:col-span-2">
          <Field label="Availability notes" value={mp.availability} placeholder="Your general availability" editing={editing} multiline onChange={v => onChange('mentor_profile.availability', v)} />
        </div>
        <SpecialismsEditor specialisms={mp.specialisms ?? []} editing={editing} onChange={onSpecialismsChange} />
        <div className="sm:col-span-2 flex items-center gap-4 text-xs text-navy-500/50">
          <span>Current scholars: <strong className="text-navy-500">{mp.current_scholar_count}</strong> / {mp.max_scholars}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${mp.has_capacity ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-500'}`}>
            {mp.has_capacity ? 'Has capacity' : 'Full'}
          </span>
        </div>

        {/* Active matches */}
        <div className="sm:col-span-2">
          <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Active Matches</p>
          {mp.active_matches?.length ? (
            <div className="space-y-2">
              {mp.active_matches.map(m => (
                <div key={m.scholar_id} className="bg-purple-50 rounded-xl px-4 py-2.5 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-navy-500">{m.scholar_name}</span>
                    <span className="text-xs text-navy-500/40">Matched {new Date(m.matched_on).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                  </div>
                  {(m.cohort_name || m.programme_name) && (
                    <p className="text-xs text-purple-600 mt-0.5">
                      {m.programme_name}{m.cohort_name ? ` — ${m.cohort_name}` : ''}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-navy-500/40 italic">No active matches — this mentor has no live scholar assignments.</p>
          )}
        </div>

        {/* Cohorts */}
        <CohortBadges user={user} />
      </div>
    </div>
  );
}

// ── Scholar profile section ───────────────────────────────────────────────────
function ScholarSection({ user, editing, onChange }: { user: User; editing: boolean; onChange: (field: string, v: string) => void }) {
  const sp = user.scholar_profile;
  if (!sp) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Scholar Profile</h2>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="Scholarship reference" value={sp.scholarship_reference} placeholder="SPT internal ID / CRM reference" editing={editing} onChange={v => onChange('scholar_profile.scholarship_reference', v)} />
        <div className="sm:col-span-2">
          <Field label="Programme goals" value={sp.goals} placeholder="What do you hope to achieve through the mentoring programme? Describe your learning objectives, career goals, or skills you want to develop." editing={editing} multiline onChange={v => onChange('scholar_profile.goals', v)} />
        </div>

        {/* Matched mentor */}
        <div className="sm:col-span-2">
          <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Matched Mentor</p>
          {sp.matched_mentor ? (
            <div className="flex items-center justify-between bg-purple-50 rounded-xl px-4 py-2.5 text-sm">
              <span className="font-semibold text-navy-500">{sp.matched_mentor.mentor_name}</span>
              <span className="text-xs text-navy-500/40">Matched {new Date(sp.matched_mentor.matched_on).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
            </div>
          ) : (
            <p className="text-sm text-navy-500/40 italic">No active mentor match</p>
          )}
        </div>

        {/* TC-23: Linked sponsor */}
        <div className="sm:col-span-2">
          <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Linked Sponsor</p>
          {sp.sponsor_name ? (
            <div className="flex items-center bg-orange-50 border border-orange-100 rounded-xl px-4 py-2.5 text-sm">
              <svg className="w-4 h-4 text-orange-400 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="font-semibold text-navy-500">{sp.sponsor_name}</span>
            </div>
          ) : (
            <p className="text-sm text-navy-500/40 italic">No sponsor linked</p>
          )}
        </div>

        {/* Cohorts */}
        <CohortBadges user={user} />

        {/* University (moved to bottom as last section to complete) */}
        <div className="sm:col-span-2 border-t border-purple-50 pt-4 mt-2">
          <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-3">University Details</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="University" value={sp.university} placeholder="Your university" editing={editing} onChange={v => onChange('scholar_profile.university', v)} />
            <Field label="Course" value={sp.course} placeholder="Your course / subject" editing={editing} onChange={v => onChange('scholar_profile.course', v)} />
            <Field label="Year of study" value={sp.year_of_study} type="number" editing={editing} onChange={v => onChange('scholar_profile.year_of_study', v)} />
            <Field label="Graduation year" value={sp.graduation_year} type="number" editing={editing} onChange={v => onChange('scholar_profile.graduation_year', v)} />
          </div>
        </div>

        {sp.soft_skills_current && Object.keys(sp.soft_skills_current).length > 0 && (
          <div className="sm:col-span-2">
            <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Soft Skills Progress</p>
            <div className="space-y-2">
              {Object.entries(sp.soft_skills_current).map(([skill, score]) => (
                <div key={skill} className="flex items-center gap-3">
                  <span className="text-xs text-navy-500/60 w-36 capitalize">{skill.replace(/_/g, ' ')}</span>
                  <div className="flex-1 bg-purple-50 rounded-full h-2">
                    <div
                      className="bg-gradient-brand-soft h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(100, (Number(score) / 10) * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-navy-500 w-6 text-right">{score}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sponsor profile section ───────────────────────────────────────────────────
function SponsorSection({ user, editing, onChange }: { user: User; editing: boolean; onChange: (field: string, v: string) => void }) {
  const sp = user.sponsor_profile;
  if (!sp) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Sponsor Profile</h2>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="Organisation" value={sp.organisation} editing={editing} onChange={v => onChange('sponsor_profile.organisation', v)} />
        <Field label="Contact name" value={sp.contact_name} editing={editing} onChange={v => onChange('sponsor_profile.contact_name', v)} />
        <Field label="Update frequency (days)" value={sp.update_frequency_days} type="number" editing={editing} onChange={v => onChange('sponsor_profile.update_frequency_days', v)} />

        {/* TC-23: Linked scholars */}
        <div className="sm:col-span-2">
          <p className="text-[10px] font-semibold text-navy-500/40 uppercase tracking-wider mb-2">Linked Scholars</p>
          {sp.sponsored_scholars?.length ? (
            <div className="space-y-1.5">
              {sp.sponsored_scholars.map(s => (
                <div key={s.id} className="flex items-center bg-purple-50 rounded-xl px-4 py-2.5 text-sm">
                  <svg className="w-4 h-4 text-purple-400 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span className="font-semibold text-navy-500">{s.full_name}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-navy-500/40 italic">No scholars linked to this sponsor account</p>
          )}
        </div>
      </div>
    </div>
  );
}



// ── Shared documents (admin → user) ──────────────────────────────────────────
interface SharedDoc {
  id: number;
  file: string;
  filename: string;
  shared_by_name: string;
  shared_at: string;
  message: string;
}

function SharedDocumentsSection() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMsg, setUploadMsg] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery<{ results: SharedDoc[] }>({
    queryKey: ['shared-documents'],
    queryFn: () => api.get('/resources/shared-documents/').then(r => r.data),
  });

  const received = data?.results ?? [];
  const matchedMentorId = user?.scholar_profile?.matched_mentor?.mentor_id ?? null;
  const matchedMentorName = user?.scholar_profile?.matched_mentor?.mentor_name ?? null;

  const uploadMutation = useMutation({
    mutationFn: (fd: FormData) =>
      api.post('/resources/shared-documents/', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shared-documents'] });
      setShowUpload(false);
      setUploadFile(null);
      setUploadMsg('');
      setRecipientEmail('');
      if (fileRef.current) fileRef.current.value = '';
    },
  });

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    const fd = new FormData();
    fd.append('file', uploadFile);
    fd.append('filename', uploadFile.name);
    if (matchedMentorId) {
      fd.append('shared_with', String(matchedMentorId));
    } else {
      fd.append('shared_with_email', recipientEmail);
    }
    if (uploadMsg) fd.append('message', uploadMsg);
    uploadMutation.mutate(fd);
  };

  if (isLoading) return null;

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <BrandStar />
          <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Shared Documents</h2>
        </div>
        <button
          type="button"
          onClick={() => setShowUpload(v => !v)}
          className="text-xs font-semibold text-pink-500 hover:text-pink-600 flex items-center gap-1 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
          </svg>
          Share a file
        </button>
      </div>

      {showUpload && (
        <form onSubmit={handleUpload} className="bg-white rounded-2xl shadow-card p-5 mb-4 space-y-3">
          <div>
            <label className="text-xs font-semibold text-navy-500 block mb-1">File</label>
            <input
              ref={fileRef}
              type="file"
              required
              onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
              className="text-xs text-navy-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-pink-50 file:text-pink-600 hover:file:bg-pink-100 w-full"
            />
          </div>
          {matchedMentorId ? (
            <p className="text-xs text-navy-500/50">
              Will be shared with your mentor, {matchedMentorName}.
            </p>
          ) : (
            <div>
              <label className="text-xs font-semibold text-navy-500 block mb-1">Recipient email</label>
              <input
                type="email"
                required
                value={recipientEmail}
                onChange={e => setRecipientEmail(e.target.value)}
                className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors"
                placeholder="recipient@example.com"
              />
            </div>
          )}
          <div>
            <label className="text-xs font-semibold text-navy-500 block mb-1">
              Message <span className="font-normal text-navy-500/40">(optional)</span>
            </label>
            <input
              type="text"
              value={uploadMsg}
              onChange={e => setUploadMsg(e.target.value)}
              className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors"
              placeholder="Add a note…"
            />
          </div>
          {uploadMutation.isError && (
            <p className="text-xs text-red-500">Upload failed. Please check the file and try again.</p>
          )}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowUpload(false)}
              className="text-xs font-semibold text-navy-500/50 hover:text-navy-500 px-3 py-2 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploadMutation.isPending || !uploadFile || (!matchedMentorId && !recipientEmail)}
              className="bg-pink-500 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-pink-600 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed shadow-brand"
            >
              {uploadMutation.isPending ? 'Uploading…' : 'Upload & share'}
            </button>
          </div>
        </form>
      )}

      {received.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-card p-6">
          <p className="text-sm text-navy-500/40 text-center py-4">No documents shared with you yet.</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-card p-6 space-y-2">
          {received.map(doc => (
            <div key={doc.id} className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-purple-50 hover:bg-purple-100 transition-colors">
              <svg className="w-5 h-5 text-purple-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <div className="flex-1 min-w-0">
                <a
                  href={doc.file}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-purple-700 hover:text-pink-600 truncate block"
                >
                  {doc.filename}
                </a>
                <p className="text-[11px] text-navy-500/40">
                  Shared by {doc.shared_by_name} · {new Date(doc.shared_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                  {doc.message && <> · <span className="italic">{doc.message}</span></>}
                </p>
              </div>
              <a
                href={doc.file}
                download={doc.filename}
                className="flex-shrink-0 text-xs font-semibold text-purple-500 hover:text-pink-500 transition-colors"
              >
                Download
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Security (change password) section ────────────────────────────────────────
function SecuritySection() {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const mutation = useMutation({
    mutationFn: (payload: { new_password: string; confirm_password: string }) =>
      api.post('/users/me/change-password/', payload),
    onSuccess: () => {
      setNewPassword('');
      setConfirmPassword('');
      setError('');
      setDone(true);
      setTimeout(() => setDone(false), 4000);
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data;
      const firstField = data && Object.values(data)[0];
      setError(Array.isArray(firstField) ? firstField[0] : 'Could not update password. Please try again.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setDone(false);
    if (!newPassword) {
      setError('Please enter a new password.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError('');
    mutation.mutate({ new_password: newPassword, confirm_password: confirmPassword });
  };

  const inputClass =
    'w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors';

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Security - change your password</h2>
      </div>
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-card p-6 space-y-4 max-w-md">
        <p className="text-xs text-navy-500/60">Change the password you use to log in.</p>
        <div>
          <label className="text-xs font-semibold text-navy-500 block mb-1">New password</label>
          <input
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={e => setNewPassword(e.target.value)}
            className={inputClass}
            placeholder="At least 8 characters"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-navy-500 block mb-1">Confirm new password</label>
          <input
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={e => setConfirmPassword(e.target.value)}
            className={inputClass}
            placeholder="Re-enter new password"
          />
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
        {done && <p className="text-xs text-green-600 font-semibold">Password updated.</p>}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={mutation.isPending || !newPassword || !confirmPassword}
            className="bg-pink-500 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-pink-600 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed shadow-brand"
          >
            {mutation.isPending ? 'Saving…' : 'Update password'}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function ProfilePage() {
  const { user, fetchCurrentUser } = useAuth();
  const queryClient = useQueryClient();
  const push = usePushNotifications();
  const location = useLocation();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<User>>({});
  const [saveError, setSaveError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user) setForm(user);
  }, [user]);

  // Deep-link support: /profile#documents or /profile#security should scroll
  // that section into view once the page (and its data) has rendered.
  useEffect(() => {
    if (!user) return;
    const hash = location.hash.replace('#', '');
    if (hash !== 'documents' && hash !== 'security') return;
    const timer = setTimeout(() => {
      document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth' });
    }, 150);
    return () => clearTimeout(timer);
  }, [user, location.hash]);

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<User>) => api.patch(`/users/${user!.id}/`, payload),
    onSuccess: async () => {
      await fetchCurrentUser();
      setEditing(false);
      setSaved(true);
      setSaveError('');
      setTimeout(() => setSaved(false), 3000);
    },
    onError: () => setSaveError('Failed to save changes. Please try again.'),
  });

  const setField = (field: string, value: string) => {
    if (field.includes('.')) {
      const [section, key] = field.split('.');
      setForm(prev => ({
        ...prev,
        [section]: { ...(prev as Record<string, unknown>)[section] as object, [key]: value },
      }));
    } else {
      setForm(prev => ({ ...prev, [field]: value }));
    }
  };

  const setSpecialisms = (specialisms: string[]) => {
    setForm(prev => ({
      ...prev,
      mentor_profile: { ...prev.mentor_profile! , specialisms },
    } as Partial<User>));
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(form);
  };

  const handleCancel = () => {
    if (user) setForm(user);
    setEditing(false);
    setSaveError('');
  };

  if (!user || !form.first_name) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
    <form onSubmit={handleSave} className="space-y-8">
      {/* Profile hero */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-8 shadow-brand">
        <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full bg-white/5" />
        <div className="relative z-10 flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-white/10 border-2 border-white/20 flex items-center justify-center text-2xl font-extrabold flex-shrink-0">
            {user.first_name[0]}{user.last_name[0]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-0.5">My Profile</p>
            <h1 className="text-2xl font-extrabold truncate">{user.full_name}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${roleBadgeStyle[user.role] ?? 'bg-white/20 text-white'}`}>
                {user.role}
              </span>
              {user.is_verified && (
                <span className="text-xs font-semibold bg-green-100 text-green-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  Verified
                </span>
              )}
              {user.cohorts?.map(c => (
                <span key={c.cohort_id} className="text-xs font-semibold bg-white/10 border border-white/20 text-white/90 px-2 py-0.5 rounded-full">
                  {c.cohort_name}
                </span>
              ))}
            </div>
          </div>
          <div className="flex-shrink-0">
            {!editing ? (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="text-xs font-semibold bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg transition-colors border border-white/20"
              >
                Edit profile
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="text-xs font-semibold bg-white/10 hover:bg-white/20 text-white px-3 py-2 rounded-lg transition-colors border border-white/20"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="text-xs font-semibold bg-pink-500 hover:bg-pink-600 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {saved && (
        <div className="bg-green-50 border border-green-100 rounded-xl px-4 py-3 text-xs text-green-700 font-medium flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          Profile updated successfully.
        </div>
      )}
      {saveError && (
        <div className="bg-red-50 border border-red-100 rounded-xl px-4 py-3 text-xs text-red-600">
          {saveError}
        </div>
      )}

      {/* Personal info */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BrandStar />
          <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Personal Information</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
          <Field label="First name" value={form.first_name} editing={editing} onChange={v => setField('first_name', v)} />
          <Field label="Last name" value={form.last_name} editing={editing} onChange={v => setField('last_name', v)} />
          <Field label="Email" value={form.email} type="email" editing={editing} onChange={v => setField('email', v)} />
          <Field label="Phone" value={form.phone} type="tel" editing={editing} onChange={v => setField('phone', v)} placeholder="+44…" />
          <Field label="Location" value={form.location} editing={editing} onChange={v => setField('location', v)} placeholder="City, Country" />
          <EngineeringDisciplinesEditor
            disciplines={form.engineering_disciplines ?? []}
            editing={editing}
            onChange={v => setForm(prev => ({ ...prev, engineering_disciplines: v }))}
          />
          <div className="sm:col-span-2">
            <Field label="Bio" value={form.bio} editing={editing} onChange={v => setField('bio', v)} multiline placeholder="Tell us about yourself…" />
          </div>
        </div>
      </div>

      {/* Notification preferences */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BrandStar />
          <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Notifications</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-card p-6 space-y-4">
          {/* Email notifications — editable only in edit mode (NOTIF-02).
              Outside edit mode this is a read-only badge; the value is saved
              together with the rest of the profile via the Save button. */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-navy-500">Email notifications</p>
              <p className="text-xs text-navy-500/40">Receive updates by email</p>
            </div>
            {editing ? (
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${form.notification_email ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {form.notification_email ? 'On' : 'Off'}
                </span>
                <input
                  type="checkbox"
                  className="accent-pink-500 w-4 h-4"
                  checked={form.notification_email ?? false}
                  onChange={e => setForm(prev => ({ ...prev, notification_email: e.target.checked }))}
                />
              </label>
            ) : (
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${form.notification_email ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {form.notification_email ? 'On' : 'Off'}
              </span>
            )}
          </div>

          {/* Browser push notifications — always interactive, independent of edit mode */}
          <div className="flex items-center justify-between border-t border-purple-50 pt-4">
            <div>
              <p className="text-sm font-semibold text-navy-500">Browser push notifications</p>
              <p className="text-xs text-navy-500/40">
                {push.permission === 'denied'
                  ? 'Blocked in your browser — allow notifications in browser settings to enable'
                  : push.isSubscribed
                    ? 'You will receive push notifications in this browser'
                    : 'Get notified even when the app is in the background'}
              </p>
            </div>
            {push.permission === 'unsupported' ? (
              <span className="text-xs text-navy-500/40">Not supported</span>
            ) : push.permission === 'denied' ? (
              <span className="text-xs text-red-400 font-semibold">Blocked</span>
            ) : push.isSubscribed ? (
              <button
                type="button"
                onClick={push.unsubscribe}
                className="text-xs font-semibold text-navy-500/50 hover:text-red-500 transition-colors"
              >
                Turn off
              </button>
            ) : (
              <button
                type="button"
                onClick={push.subscribe}
                className="text-xs font-semibold bg-pink-500 text-white px-3 py-1.5 rounded-lg hover:bg-pink-600 transition-colors shadow-brand"
              >
                Enable
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Role-specific sections */}
      {user.role === 'mentor' && (
        <MentorSection user={form as User} editing={editing} onChange={setField} onSpecialismsChange={setSpecialisms} />
      )}
      {(user.role === 'scholar' || user.role === 'alumni') && (
        <ScholarSection user={form as User} editing={editing} onChange={setField} />
      )}
      {user.role === 'sponsor' && (
        <SponsorSection user={form as User} editing={editing} onChange={setField} />
      )}

    </form>
    {/* Rendered OUTSIDE the profile <form>: this section has its own upload
        <form>, and a nested form is invalid HTML — the inner submit never
        fires, so uploads silently never send. Keep it a sibling. */}
    {/* id wrappers stay mounted regardless of the sections' own loading
        state, so the #documents / #security deep links always have a
        target to scroll to. */}
    <div id="documents">
      <SharedDocumentsSection />
    </div>
    <div id="security">
      <SecuritySection />
    </div>
    </div>
  );
}
