import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
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
      <p className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-1">{label}</p>
      {editing ? (
        multiline ? (
          <textarea
            className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 resize-none"
            rows={3}
            placeholder={placeholder}
            value={String(value ?? '')}
            onChange={e => onChange?.(e.target.value)}
          />
        ) : (
          <input
            type={type}
            className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30"
            placeholder={placeholder}
            value={String(value ?? '')}
            onChange={e => onChange?.(e.target.value)}
          />
        )
      ) : (
        <p className="text-sm text-navy-DEFAULT">{display}</p>
      )}
    </div>
  );
}

// ── Mentor profile section ────────────────────────────────────────────────────
function MentorSection({ user, editing, onChange }: { user: User; editing: boolean; onChange: (field: string, v: string) => void }) {
  const mp = user.mentor_profile;
  if (!mp) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Mentor Profile</h2>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="Company" value={mp.company} placeholder="Your employer" editing={editing} onChange={v => onChange('mentor_profile.company', v)} />
        <Field label="Job Title" value={mp.job_title} placeholder="Your role" editing={editing} onChange={v => onChange('mentor_profile.job_title', v)} />
        <Field label="Years Experience" value={mp.years_experience} type="number" editing={editing} onChange={v => onChange('mentor_profile.years_experience', v)} />
        <Field label="Max scholars" value={mp.max_scholars} type="number" editing={editing} onChange={v => onChange('mentor_profile.max_scholars', v)} />
        <div className="sm:col-span-2">
          <Field label="Availability notes" value={mp.availability} placeholder="Your general availability" editing={editing} multiline onChange={v => onChange('mentor_profile.availability', v)} />
        </div>
        <div className="sm:col-span-2">
          <p className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-1">Specialisms</p>
          <p className="text-sm text-navy-DEFAULT">{mp.specialisms?.join(', ') || '—'}</p>
        </div>
        <div className="sm:col-span-2 flex items-center gap-4 text-xs text-navy-DEFAULT/50">
          <span>Current scholars: <strong className="text-navy-DEFAULT">{mp.current_scholar_count}</strong> / {mp.max_scholars}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${mp.has_capacity ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-500'}`}>
            {mp.has_capacity ? 'Has capacity' : 'Full'}
          </span>
        </div>
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
        <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Scholar Profile</h2>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="University" value={sp.university} placeholder="Your university" editing={editing} onChange={v => onChange('scholar_profile.university', v)} />
        <Field label="Course" value={sp.course} placeholder="Your course" editing={editing} onChange={v => onChange('scholar_profile.course', v)} />
        <Field label="Year of study" value={sp.year_of_study} type="number" editing={editing} onChange={v => onChange('scholar_profile.year_of_study', v)} />
        <Field label="Graduation year" value={sp.graduation_year} type="number" editing={editing} onChange={v => onChange('scholar_profile.graduation_year', v)} />
        <Field label="Scholarship reference" value={sp.scholarship_reference} editing={editing} onChange={v => onChange('scholar_profile.scholarship_reference', v)} />
        <div className="sm:col-span-2">
          <Field label="Goals" value={sp.goals} placeholder="Your programme goals" editing={editing} multiline onChange={v => onChange('scholar_profile.goals', v)} />
        </div>
        {sp.soft_skills_current && Object.keys(sp.soft_skills_current).length > 0 && (
          <div className="sm:col-span-2">
            <p className="text-[10px] font-semibold text-navy-DEFAULT/40 uppercase tracking-wider mb-2">Soft Skills Progress</p>
            <div className="space-y-2">
              {Object.entries(sp.soft_skills_current).map(([skill, score]) => (
                <div key={skill} className="flex items-center gap-3">
                  <span className="text-xs text-navy-DEFAULT/60 w-36 capitalize">{skill.replace(/_/g, ' ')}</span>
                  <div className="flex-1 bg-purple-50 rounded-full h-2">
                    <div
                      className="bg-gradient-brand-soft h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(100, (Number(score) / 10) * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-navy-DEFAULT w-6 text-right">{score}</span>
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
        <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Sponsor Profile</h2>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Field label="Organisation" value={sp.organisation} editing={editing} onChange={v => onChange('sponsor_profile.organisation', v)} />
        <Field label="Contact name" value={sp.contact_name} editing={editing} onChange={v => onChange('sponsor_profile.contact_name', v)} />
        <Field label="Update frequency (days)" value={sp.update_frequency_days} type="number" editing={editing} onChange={v => onChange('sponsor_profile.update_frequency_days', v)} />
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function ProfilePage() {
  const { user, fetchCurrentUser } = useAuth();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<User>>({});
  const [saveError, setSaveError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user) setForm(user);
  }, [user]);

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
        <div className="w-8 h-8 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" />
      </div>
    );
  }

  return (
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
            <div className="flex items-center gap-2 mt-1">
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
                  className="text-xs font-semibold bg-pink-DEFAULT hover:bg-pink-600 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
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
          <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Personal Information</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-card p-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
          <Field label="First name" value={form.first_name} editing={editing} onChange={v => setField('first_name', v)} />
          <Field label="Last name" value={form.last_name} editing={editing} onChange={v => setField('last_name', v)} />
          <Field label="Email" value={form.email} type="email" editing={editing} onChange={v => setField('email', v)} />
          <Field label="Phone" value={form.phone} type="tel" editing={editing} onChange={v => setField('phone', v)} placeholder="+44…" />
          <Field label="Location" value={form.location} editing={editing} onChange={v => setField('location', v)} placeholder="City, Country" />
          <Field label="Engineering discipline" value={form.engineering_discipline} editing={editing} onChange={v => setField('engineering_discipline', v)} />
          <div className="sm:col-span-2">
            <Field label="Bio" value={form.bio} editing={editing} onChange={v => setField('bio', v)} multiline placeholder="Tell us about yourself…" />
          </div>
        </div>
      </div>

      {/* Notification preferences */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BrandStar />
          <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Notifications</h2>
        </div>
        <div className="bg-white rounded-2xl shadow-card p-6 space-y-3">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="text-sm font-semibold text-navy-DEFAULT">Email notifications</p>
              <p className="text-xs text-navy-DEFAULT/40">Receive updates by email</p>
            </div>
            <input
              type="checkbox"
              className="accent-pink-DEFAULT w-4 h-4"
              checked={form.notification_email ?? false}
              onChange={e => setForm(prev => ({ ...prev, notification_email: e.target.checked }))}
              disabled={!editing}
            />
          </label>
        </div>
      </div>

      {/* Role-specific sections */}
      {user.role === 'mentor' && (
        <MentorSection user={form as User} editing={editing} onChange={setField} />
      )}
      {(user.role === 'scholar' || user.role === 'alumni') && (
        <ScholarSection user={form as User} editing={editing} onChange={setField} />
      )}
      {user.role === 'sponsor' && (
        <SponsorSection user={form as User} editing={editing} onChange={setField} />
      )}
    </form>
  );
}
