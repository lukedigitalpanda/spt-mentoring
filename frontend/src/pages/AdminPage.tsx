import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';

type Tab = 'dashboard' | 'contact-report' | 'sponsor-updates' | 'users' | 'moderation' | 'mass-message' | 'msg-export' | 'waiting-list' | 'sessions' | 'programmes' | 'cohorts' | 'news' | 'resources' | 'forums' | 'settings';

const tabs: [Tab, string][] = [
  ['dashboard',       '📊 Dashboard'],
  ['users',           'Users'],
  ['programmes',      'Programmes'],
  ['cohorts',         'Cohorts'],
  ['news',            'News'],
  ['resources',       'Resources'],
  ['forums',          'Forums'],
  ['sessions',        'Sessions'],
  ['moderation',      'Moderation'],
  ['mass-message',    'Mass Message'],
  ['msg-export',      'Message Export'],
  ['waiting-list',    'Waiting List'],
  ['contact-report',  'Contact Report'],
  ['sponsor-updates', 'Sponsor Updates'],
  ['settings',        'Settings'],
];

// ── Shared helpers ────────────────────────────────────────────────────────────
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const inputCls = "w-full border-2 border-purple-100 rounded-xl px-4 py-2.5 text-sm text-navy-500 bg-white focus:outline-none focus:border-pink-500 transition-colors";
const labelCls = "block text-xs font-bold text-navy-500 uppercase tracking-wider mb-1.5";

function SectionHeader({ title, sub, csvHref }: { title: string; sub?: string; csvHref?: string }) {
  return (
    <div className="flex justify-between items-start mb-5">
      <div>
        <h2 className="text-lg font-extrabold text-navy-500">{title}</h2>
        {sub && <p className="text-sm text-navy-500/50 mt-0.5">{sub}</p>}
      </div>
      {csvHref && (
        <a href={csvHref}
          className="inline-flex items-center gap-1.5 border-2 border-purple-200 text-purple-500 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-purple-50 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          Export CSV
        </a>
      )}
    </div>
  );
}

function DataTable({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-2xl shadow-card overflow-x-auto">
      <table className="w-full text-sm min-w-max">
        <thead>
          <tr className="bg-gradient-brand-pale">
            {headers.map(h => (
              <th key={h} className="text-left px-4 py-3 text-xs font-bold text-navy-500 uppercase tracking-wider">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-purple-50">{children}</tbody>
      </table>
    </div>
  );
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
      ok ? 'bg-purple-100 text-purple-700' : 'bg-pink-100 text-pink-700'
    }`}>
      {label}
    </span>
  );
}

// ── Tab components ────────────────────────────────────────────────────────────
function ContactReportTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-contact'],
    queryFn: () => api.get('/reports/contact/').then(r => r.data),
  });
  if (isLoading) return <p className="text-navy-500/40 text-sm">Loading…</p>;
  const overdue = data?.results?.filter((r: any) => r.needs_chase).length ?? 0;
  return (
    <div>
      <SectionHeader
        title="Scholar / Mentor Contact Report"
        sub={`${overdue} pair${overdue !== 1 ? 's' : ''} need chasing (no contact in ${data?.threshold_days} days)`}
        csvHref={`${API}/reports/contact/?format=csv`}
      />
      <DataTable headers={['Scholar', 'Mentor', 'Last from Scholar', 'Last from Mentor', 'Status']}>
        {data?.results?.map((row: any) => (
          <tr key={`${row.scholar_id}-${row.mentor_id}`} className={row.needs_chase ? 'bg-pink-50/50' : ''}>
            <td className="px-4 py-3">
              <p className="font-semibold text-navy-500">{row.scholar_name}</p>
              <p className="text-[11px] text-navy-500/40">{row.scholar_email}</p>
            </td>
            <td className="px-4 py-3">
              <p className="font-semibold text-navy-500">{row.mentor_name}</p>
              <p className="text-[11px] text-navy-500/40">{row.mentor_email}</p>
            </td>
            <td className="px-4 py-3 text-navy-500/60">
              {row.scholar_last_message ? new Date(row.scholar_last_message).toLocaleDateString('en-GB') : 'Never'}
            </td>
            <td className="px-4 py-3 text-navy-500/60">
              {row.mentor_last_message ? new Date(row.mentor_last_message).toLocaleDateString('en-GB') : 'Never'}
            </td>
            <td className="px-4 py-3">
              <Badge ok={!row.needs_chase} label={row.needs_chase ? 'Needs chasing' : 'Active'} />
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}

function SponsorUpdateTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-sponsor'],
    queryFn: () => api.get('/reports/sponsor-updates/').then(r => r.data),
  });
  if (isLoading) return <p className="text-navy-500/40 text-sm">Loading…</p>;
  return (
    <div>
      <SectionHeader
        title="Sponsor Update Report"
        sub="Scholars' contact frequency with their sponsors"
        csvHref={`${API}/reports/sponsor-updates/?format=csv`}
      />
      <DataTable headers={['Scholar', 'Sponsor', 'Last Update', 'Days Since', 'Status']}>
        {data?.results?.map((row: any) => (
          <tr key={row.scholar_id} className={row.is_overdue ? 'bg-orange-50/50' : ''}>
            <td className="px-4 py-3 font-semibold text-navy-500">{row.scholar_name}</td>
            <td className="px-4 py-3 text-navy-500/60">{row.sponsor_name || '—'}</td>
            <td className="px-4 py-3 text-navy-500/60">
              {row.last_update_sent ? new Date(row.last_update_sent).toLocaleDateString('en-GB') : 'Never'}
            </td>
            <td className="px-4 py-3 text-navy-500/60">{row.days_since_update ?? '—'}</td>
            <td className="px-4 py-3">
              <Badge ok={!row.is_overdue} label={row.is_overdue ? 'Overdue' : 'Up to date'} />
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}

function UserManagementTab() {
  const [search, setSearch] = useState('');
  const { data } = useQuery({
    queryKey: ['admin-users', search],
    queryFn: () => api.get(`/users/?search=${search}`).then(r => r.data),
  });
  const roleColour: Record<string, string> = {
    scholar: 'bg-purple-100 text-purple-700',
    mentor:  'bg-navy-100 text-navy-700',
    sponsor: 'bg-orange-100 text-orange-700',
    alumni:  'bg-pink-100 text-pink-700',
    admin:   'bg-gradient-brand-soft text-white',
  };
  return (
    <div>
      <div className="flex justify-between items-start mb-5">
        <div>
          <h2 className="text-lg font-extrabold text-navy-500">User Management</h2>
          <p className="text-sm text-navy-500/50 mt-0.5">{data?.count ?? '…'} users</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name, email, CRM ID…"
            className="border-2 border-purple-100 rounded-xl px-3 py-1.5 text-sm text-navy-500 focus:outline-none focus:border-pink-500 transition-colors w-64"
          />
          <a href={`${API}/users/export/`}
            className="inline-flex items-center gap-1.5 border-2 border-purple-200 text-purple-500 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-purple-50"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
            Export CSV
          </a>
        </div>
      </div>
      <DataTable headers={['Name', 'Email', 'Role', 'Location', 'Status']}>
        {data?.results?.map((u: any) => (
          <tr key={u.id}>
            <td className="px-4 py-3 font-semibold text-navy-500">{u.full_name}</td>
            <td className="px-4 py-3 text-navy-500/60">{u.email}</td>
            <td className="px-4 py-3">
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full capitalize ${roleColour[u.role] || 'bg-gray-100 text-gray-600'}`}>
                {u.role}
              </span>
            </td>
            <td className="px-4 py-3 text-navy-500/60">{u.location || '—'}</td>
            <td className="px-4 py-3">
              <Badge ok={u.is_active} label={u.is_active ? 'Active' : 'Inactive'} />
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}

function ModerationQueueTab() {
  const { data, refetch } = useQuery({
    queryKey: ['flagged-messages'],
    queryFn: () => api.get('/moderation/flagged-messages/').then(r => r.data),
  });
  const approve = async (id: number) => { await api.post(`/moderation/flagged-messages/${id}/approve/`); refetch(); };
  const reject  = async (id: number) => { await api.post(`/moderation/flagged-messages/${id}/reject/`); refetch(); };

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-lg font-extrabold text-navy-500">Moderation Queue</h2>
        {data?.length > 0 && (
          <span className="bg-pink-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {data.length}
          </span>
        )}
      </div>
      {(!data || data.length === 0) ? (
        <div className="text-center py-16 bg-white rounded-2xl shadow-card text-navy-500/30">
          <svg className="w-10 h-10 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <p className="font-semibold text-sm">All clear – no flagged messages</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((msg: any) => (
            <div key={msg.id} className="bg-white rounded-2xl shadow-card border-l-4 border-orange-500 p-5">
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-orange-500 uppercase tracking-wider mb-1">{msg.moderation_note}</p>
                  <p className="font-semibold text-navy-500 text-sm">{msg.sender_name}</p>
                  <p className="text-sm text-navy-500/70 mt-1 line-clamp-3">{msg.body}</p>
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  <button onClick={() => approve(msg.id)}
                    className="text-xs bg-purple-100 text-purple-700 font-bold px-3 py-1.5 rounded-lg hover:bg-purple-200 transition-colors">
                    Approve
                  </button>
                  <button onClick={() => reject(msg.id)}
                    className="text-xs bg-pink-100 text-pink-700 font-bold px-3 py-1.5 rounded-lg hover:bg-pink-200 transition-colors">
                    Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MassMessageTab() {
  const [subject, setSubject]               = useState('');
  const [body, setBody]                     = useState('');
  const [roles, setRoles]                   = useState<string[]>([]);
  const [selectedProgrammes, setSelectedProgrammes] = useState<number[]>([]);
  const [selectedCohorts, setSelectedCohorts]       = useState<number[]>([]);
  const [sending, setSending]               = useState(false);
  const [sent, setSent]                     = useState<{ count: number; subject: string } | null>(null);
  const [error, setError]                   = useState('');

  const { data: programmesData } = useQuery({
    queryKey: ['admin-programmes'],
    queryFn: () => api.get('/cohorts/programmes/?page_size=100').then(r => r.data),
  });
  const programmes: any[] = programmesData?.results ?? [];

  const { data: cohortsData } = useQuery({
    queryKey: ['admin-cohorts-mm'],
    queryFn: () => api.get('/cohorts/cohorts/?page_size=100').then(r => r.data),
  });
  const cohorts: any[] = cohortsData?.results ?? [];

  const ALL_ROLES = ['scholar', 'mentor', 'sponsor', 'alumni'];
  const toggleRole = (role: string) =>
    setRoles(prev => prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]);
  const toggleEveryone = () =>
    setRoles(prev => ALL_ROLES.every(r => prev.includes(r)) ? [] : ALL_ROLES);

  const toggleProgramme = (id: number) =>
    setSelectedProgrammes(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]);
  const toggleCohort = (id: number) =>
    setSelectedCohorts(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);

  const sendMassMessage = async () => {
    if (!subject.trim() || !body.trim() || roles.length === 0) return;
    setSending(true);
    setError('');
    try {
      const { data } = await api.post('/messaging/mass-messages/', {
        subject,
        body,
        recipient_roles: roles,
        recipient_programmes: selectedProgrammes,
        recipient_cohorts: selectedCohorts,
        send_from_email: 'mentoring@smallpeicetrust.org.uk',
      });
      const sendResp = await api.post(`/messaging/mass-messages/${data.id}/send/`);
      const count = sendResp.data?.recipient_count ?? '?';
      setSent({ count, subject });
      setSubject(''); setBody(''); setRoles([]); setSelectedProgrammes([]); setSelectedCohorts([]);
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const mmInputCls = "w-full border-2 border-purple-100 rounded-xl px-4 py-2.5 text-sm text-navy-500 bg-white focus:outline-none focus:border-pink-500 transition-colors";
  const mmLabelCls = "block text-xs font-bold text-navy-500 uppercase tracking-wider mb-2";

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-extrabold text-navy-500">Mass Message</h2>
        <p className="text-sm text-navy-500/50 mt-0.5">
          Messages are delivered as a conversation from <span className="font-semibold text-navy-500">Arkwright</span> in each recipient's inbox.
        </p>
      </div>

      {/* Success state */}
      {sent && (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-5 flex items-start gap-3">
          <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-bold text-green-800">Message sent!</p>
            <p className="text-xs text-green-700/80 mt-0.5">
              "{sent.subject}" was delivered to {sent.count} recipient{sent.count !== 1 ? 's' : ''} as a conversation from Arkwright.
            </p>
          </div>
          <button onClick={() => setSent(null)} className="text-green-500 hover:text-green-700">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-card p-6 space-y-5">

        {/* Sender identity */}
        <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-xl">
          <div className="w-9 h-9 rounded-xl bg-gradient-brand-soft flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-extrabold">A</span>
          </div>
          <div>
            <p className="text-sm font-bold text-navy-500">Arkwright</p>
            <p className="text-xs text-navy-500/50">System account — recipients will see this as a conversation from Arkwright</p>
          </div>
        </div>

        {/* Role filter */}
        <div>
          <label className={mmLabelCls}>Send to — user type <span className="text-pink-500">*</span></label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={toggleEveryone}
              className={`text-xs font-semibold px-4 py-2 rounded-lg border-2 transition-all ${
                ALL_ROLES.every(r => roles.includes(r))
                  ? 'bg-navy-500 text-white border-navy-500'
                  : 'border-purple-100 text-navy-500/60 hover:border-purple-300'
              }`}
            >
              Everyone
            </button>
            {[
              { key: 'scholar', label: 'Scholars' },
              { key: 'mentor',  label: 'Mentors'  },
              { key: 'sponsor', label: 'Sponsors' },
              { key: 'alumni',  label: 'Alumni'   },
            ].map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => toggleRole(key)}
                className={`text-xs font-semibold px-4 py-2 rounded-lg border-2 transition-all ${
                  roles.includes(key)
                    ? 'bg-pink-500 text-white border-pink-500'
                    : 'border-purple-100 text-navy-500/60 hover:border-purple-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Programme filter */}
        <div>
          <label className={mmLabelCls}>
            Filter by programme
            <span className="ml-1 font-normal text-navy-500/40 normal-case">(optional — leave blank for all)</span>
          </label>
          {programmes.length === 0 ? (
            <p className="text-xs text-navy-500/40">No programmes found.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {programmes.map((p: any) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => toggleProgramme(p.id)}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-lg border-2 transition-all ${
                    selectedProgrammes.includes(p.id)
                      ? 'bg-purple-500 text-white border-purple-500'
                      : 'border-purple-100 text-navy-500/60 hover:border-purple-300'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          )}
          {selectedProgrammes.length > 0 && (
            <p className="text-[11px] text-navy-500/40 mt-1.5">
              Only members of {selectedProgrammes.length} selected programme{selectedProgrammes.length !== 1 ? 's' : ''} will receive this message.
            </p>
          )}
        </div>

        {/* Cohort filter */}
        <div>
          <label className={mmLabelCls}>
            Filter by cohort
            <span className="ml-1 font-normal text-navy-500/40 normal-case">(optional — leave blank for all)</span>
          </label>
          {cohorts.length === 0 ? (
            <p className="text-xs text-navy-500/40">No cohorts found.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {cohorts.map((c: any) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => toggleCohort(c.id)}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-lg border-2 transition-all ${
                    selectedCohorts.includes(c.id)
                      ? 'bg-pink-500 text-white border-pink-500'
                      : 'border-purple-100 text-navy-500/60 hover:border-purple-300'
                  }`}
                >
                  {c.name}
                </button>
              ))}
            </div>
          )}
          {selectedCohorts.length > 0 && (
            <p className="text-[11px] text-navy-500/40 mt-1.5">
              Only members of {selectedCohorts.length} selected cohort{selectedCohorts.length !== 1 ? 's' : ''} will receive this message.
            </p>
          )}
        </div>

        {/* Subject */}
        <div>
          <label className={mmLabelCls}>Subject <span className="text-pink-500">*</span></label>
          <input
            value={subject}
            onChange={e => setSubject(e.target.value)}
            placeholder="e.g. Important update from the SPT team"
            className={mmInputCls}
          />
        </div>

        {/* Body */}
        <div>
          <label className={mmLabelCls}>Message <span className="text-pink-500">*</span></label>
          <textarea
            value={body}
            onChange={e => setBody(e.target.value)}
            rows={7}
            placeholder="Write your message here…"
            className={`${mmInputCls} resize-none`}
          />
        </div>

        {error && (
          <p className="text-xs text-red-500 font-semibold">{error}</p>
        )}

        <div className="flex items-center justify-between pt-1">
          <p className="text-xs text-navy-500/40">
            {roles.length > 0
              ? `Sending to all ${roles.join(', ')}${selectedProgrammes.length ? ` in ${selectedProgrammes.length} programme(s)` : ''}${selectedCohorts.length ? ` / ${selectedCohorts.length} cohort(s)` : ''}`
              : 'Select at least one user type'}
          </p>
          <button
            onClick={sendMassMessage}
            disabled={!subject.trim() || !body.trim() || roles.length === 0 || sending}
            className="bg-gradient-brand-soft text-white px-6 py-2.5 rounded-xl text-sm font-bold hover:opacity-90 disabled:opacity-40 transition-all shadow-brand flex items-center gap-2"
          >
            {sending ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Sending…
              </>
            ) : (
              <>
                Send message
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Programmes tab ─────────────────────────────────────────────────────────────
function ProgrammesTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ name: '', description: '', start_date: '', end_date: '', is_active: true, branding_colour: '#7c3aed' });

  const { data, isLoading } = useQuery({
    queryKey: ['admin-programmes'],
    queryFn: () => api.get('/cohorts/programmes/?page_size=100').then(r => r.data),
  });
  const programmes: any[] = data?.results ?? [];

  const saveMutation = useMutation({
    mutationFn: (payload: any) =>
      editing
        ? api.patch(`/cohorts/programmes/${editing.id}/`, payload).then(r => r.data)
        : api.post('/cohorts/programmes/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-programmes'] });
      setShowForm(false);
      setEditing(null);
      setForm({ name: '', description: '', start_date: '', end_date: '', is_active: true, branding_colour: '#7c3aed' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/cohorts/programmes/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-programmes'] }),
  });

  const openEdit = (p: any) => {
    setEditing(p);
    setForm({ name: p.name, description: p.description || '', start_date: p.start_date || '', end_date: p.end_date || '', is_active: p.is_active, branding_colour: p.branding_colour || '#7c3aed' });
    setShowForm(true);
  };

  const handleDelete = (p: any) => {
    if (window.confirm(`Delete programme "${p.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(p.id);
    }
  };

  const handleSave = () => {
    const payload: any = { ...form };
    if (!payload.start_date) delete payload.start_date;
    if (!payload.end_date) delete payload.end_date;
    saveMutation.mutate(payload);
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-5">
        <div>
          <h2 className="text-lg font-extrabold text-navy-500">Programmes</h2>
          <p className="text-sm text-navy-500/50 mt-0.5">{programmes.length} programme{programmes.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => { setEditing(null); setForm({ name: '', description: '', start_date: '', end_date: '', is_active: true, branding_colour: '#7c3aed' }); setShowForm(v => !v); }}
          className="bg-pink-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-pink-600"
        >
          + New Programme
        </button>
      </div>

      {showForm && (
        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 mb-5 space-y-4">
          <h3 className="text-sm font-bold text-navy-500">{editing ? 'Edit Programme' : 'New Programme'}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Name</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Programme name" />
            </div>
            <div>
              <label className={labelCls}>Branding Colour</label>
              <input type="color" value={form.branding_colour} onChange={e => setForm(f => ({ ...f, branding_colour: e.target.value }))} className="w-full h-10 border-2 border-purple-100 rounded-xl px-2 py-1 bg-white cursor-pointer" />
            </div>
            <div>
              <label className={labelCls}>Start Date</label>
              <input type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>End Date</label>
              <input type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} className={inputCls} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Description</label>
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className={`${inputCls} resize-none`} placeholder="Optional description…" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="prog-active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              <label htmlFor="prog-active" className="text-sm text-navy-500 font-semibold">Active</label>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={handleSave} disabled={saveMutation.isPending} className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand">
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
            <button onClick={() => { setShowForm(false); setEditing(null); }} className="text-sm text-navy-500/60 px-4 py-2 rounded-xl border border-gray-200 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {programmes.length === 0 ? (
        <p className="text-center py-12 text-sm text-navy-500/40">No programmes yet. Create one above.</p>
      ) : (
        <DataTable headers={['Name', 'Dates', 'Status', 'Actions']}>
          {programmes.map((p: any) => (
            <tr key={p.id} className="hover:bg-purple-50/30">
              <td className="px-4 py-3 font-semibold text-navy-500">
                <div className="flex items-center gap-2">
                  {p.branding_colour && <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: p.branding_colour }} />}
                  {p.name}
                </div>
              </td>
              <td className="px-4 py-3 text-xs text-navy-500/60">
                {p.start_date
                  ? `${new Date(p.start_date).toLocaleDateString('en-GB')} – ${p.end_date ? new Date(p.end_date).toLocaleDateString('en-GB') : 'Ongoing'}`
                  : 'Ongoing'}
              </td>
              <td className="px-4 py-3">
                <Badge ok={p.is_active} label={p.is_active ? 'Active' : 'Inactive'} />
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <button onClick={() => openEdit(p)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Edit</button>
                  <button onClick={() => handleDelete(p)} className="text-xs text-red-500 hover:text-red-700 font-semibold">Delete</button>
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}

// ── Cohorts tab ────────────────────────────────────────────────────────────────
function CohortsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [filterProgramme, setFilterProgramme] = useState('');
  const [membersPanel, setMembersPanel] = useState<number | null>(null);
  const [userSearch, setUserSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [form, setForm] = useState({ programme: '', name: '', year: new Date().getFullYear(), description: '', is_active: true });

  const { data: programmesData } = useQuery({
    queryKey: ['admin-programmes'],
    queryFn: () => api.get('/cohorts/programmes/?page_size=100').then(r => r.data),
  });
  const programmes: any[] = programmesData?.results ?? [];

  const { data: cohortsData, isLoading } = useQuery({
    queryKey: ['admin-cohorts', filterProgramme],
    queryFn: () => api.get(`/cohorts/cohorts/?page_size=100${filterProgramme ? `&programme=${filterProgramme}` : ''}`).then(r => r.data),
  });
  const cohorts: any[] = cohortsData?.results ?? [];

  const { data: membershipsData, refetch: refetchMemberships } = useQuery({
    queryKey: ['cohort-members', membersPanel],
    queryFn: () => membersPanel ? api.get(`/cohorts/memberships/?cohort=${membersPanel}`).then(r => r.data) : null,
    enabled: !!membersPanel,
  });
  const memberships: any[] = membershipsData?.results ?? membershipsData ?? [];

  const { data: userSearchData } = useQuery({
    queryKey: ['user-search', userSearch],
    queryFn: () => userSearch.length >= 2 ? api.get(`/users/?search=${userSearch}`).then(r => r.data) : null,
    enabled: userSearch.length >= 2,
  });
  const searchedUsers: any[] = userSearchData?.results ?? [];

  const saveMutation = useMutation({
    mutationFn: (payload: any) =>
      editing
        ? api.patch(`/cohorts/cohorts/${editing.id}/`, payload).then(r => r.data)
        : api.post('/cohorts/cohorts/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-cohorts'] });
      setShowForm(false);
      setEditing(null);
      setForm({ programme: '', name: '', year: new Date().getFullYear(), description: '', is_active: true });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/cohorts/cohorts/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-cohorts'] }),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (membershipId: number) => api.delete(`/cohorts/memberships/${membershipId}/`),
    onSuccess: () => refetchMemberships(),
  });

  const addMemberMutation = useMutation({
    mutationFn: (payload: any) => api.post('/cohorts/memberships/', payload).then(r => r.data),
    onSuccess: () => { refetchMemberships(); setSelectedUser(null); setUserSearch(''); },
  });

  const openEdit = (c: any) => {
    setEditing(c);
    setForm({ programme: c.programme, name: c.name, year: c.year, description: c.description || '', is_active: c.is_active });
    setShowForm(true);
  };

  const handleDelete = (c: any) => {
    if (window.confirm(`Delete cohort "${c.name}"? This cannot be undone.`)) deleteMutation.mutate(c.id);
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-5">
        <div>
          <h2 className="text-lg font-extrabold text-navy-500">Cohorts</h2>
          <p className="text-sm text-navy-500/50 mt-0.5">{cohorts.length} cohort{cohorts.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={filterProgramme} onChange={e => setFilterProgramme(e.target.value)} className="border-2 border-purple-100 rounded-xl px-3 py-1.5 text-sm text-navy-500 focus:outline-none focus:border-pink-500">
            <option value="">All Programmes</option>
            {programmes.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button
            onClick={() => { setEditing(null); setForm({ programme: '', name: '', year: new Date().getFullYear(), description: '', is_active: true }); setShowForm(v => !v); }}
            className="bg-pink-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-pink-600"
          >
            + New Cohort
          </button>
        </div>
      </div>

      {showForm && (
        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 mb-5 space-y-4">
          <h3 className="text-sm font-bold text-navy-500">{editing ? 'Edit Cohort' : 'New Cohort'}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Programme</label>
              <select value={form.programme} onChange={e => setForm(f => ({ ...f, programme: e.target.value }))} className={inputCls}>
                <option value="">Select programme…</option>
                {programmes.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Name</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Cohort name" />
            </div>
            <div>
              <label className={labelCls}>Year</label>
              <input type="number" value={form.year} onChange={e => setForm(f => ({ ...f, year: parseInt(e.target.value) }))} className={inputCls} />
            </div>
            <div className="flex items-center gap-2 pt-6">
              <input type="checkbox" id="cohort-active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="rounded" />
              <label htmlFor="cohort-active" className="text-sm text-navy-500 font-semibold">Active</label>
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Description</label>
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} className={`${inputCls} resize-none`} placeholder="Optional…" />
            </div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={() => saveMutation.mutate(form)} disabled={saveMutation.isPending} className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand">
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
            <button onClick={() => { setShowForm(false); setEditing(null); }} className="text-sm text-navy-500/60 px-4 py-2 rounded-xl border border-gray-200 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {cohorts.length === 0 ? (
        <p className="text-center py-12 text-sm text-navy-500/40">No cohorts yet.</p>
      ) : (
        <DataTable headers={['Programme', 'Cohort', 'Year', 'Members', 'Status', 'Actions']}>
          {cohorts.map((c: any) => (
            <React.Fragment key={c.id}>
              <tr className="hover:bg-purple-50/30">
                <td className="px-4 py-3 text-xs text-navy-500/60">{c.programme_name || '—'}</td>
                <td className="px-4 py-3 font-semibold text-navy-500">{c.name}</td>
                <td className="px-4 py-3 text-xs text-navy-500/60">{c.year}</td>
                <td className="px-4 py-3 text-xs text-navy-500/60">{c.member_count ?? '—'}</td>
                <td className="px-4 py-3"><Badge ok={c.is_active} label={c.is_active ? 'Active' : 'Inactive'} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <button onClick={() => setMembersPanel(membersPanel === c.id ? null : c.id)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Members</button>
                    <button onClick={() => openEdit(c)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Edit</button>
                    <button onClick={() => handleDelete(c)} className="text-xs text-red-500 hover:text-red-700 font-semibold">Delete</button>
                  </div>
                </td>
              </tr>
              {membersPanel === c.id && (
                <tr>
                  <td colSpan={6} className="px-4 py-0">
                    <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 my-3 space-y-4">
                      <h4 className="text-sm font-bold text-navy-500">Members — {c.name}</h4>
                      {memberships.length === 0 ? (
                        <p className="text-xs text-navy-500/40">No members yet.</p>
                      ) : (
                        <div className="space-y-2">
                          {memberships.map((m: any) => (
                            <div key={m.id} className="flex items-center justify-between bg-white rounded-xl px-4 py-2.5">
                              <div>
                                <span className="text-sm font-semibold text-navy-500">{m.user_name || m.user}</span>
                                <span className="ml-2 text-xs text-navy-500/40 capitalize">{m.role}</span>
                              </div>
                              <button onClick={() => removeMemberMutation.mutate(m.id)} className="text-xs text-red-500 hover:text-red-700 font-semibold">Remove</button>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="pt-2 border-t border-purple-200">
                        <label className={labelCls}>Add Member</label>
                        <div className="flex gap-2">
                          <input
                            value={userSearch}
                            onChange={e => { setUserSearch(e.target.value); setSelectedUser(null); }}
                            placeholder="Search users by name or email…"
                            className={`${inputCls} flex-1`}
                          />
                          <button
                            onClick={() => { if (selectedUser) addMemberMutation.mutate({ cohort: c.id, user: selectedUser.id }); }}
                            disabled={!selectedUser || addMemberMutation.isPending}
                            className="bg-gradient-brand-soft text-white px-4 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand disabled:opacity-40"
                          >
                            Add
                          </button>
                        </div>
                        {searchedUsers.length > 0 && !selectedUser && (
                          <div className="bg-white border border-purple-100 rounded-xl mt-1 overflow-hidden shadow-card">
                            {searchedUsers.slice(0, 5).map((u: any) => (
                              <button key={u.id} onClick={() => { setSelectedUser(u); setUserSearch(u.full_name); }}
                                className="w-full text-left px-4 py-2 hover:bg-purple-50 text-sm text-navy-500 border-b border-purple-50 last:border-0">
                                {u.full_name} <span className="text-navy-500/40 text-xs">({u.email})</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </DataTable>
      )}
    </div>
  );
}

// ── News tab ───────────────────────────────────────────────────────────────────
function NewsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ title: '', summary: '', body: '', audience: 'all', is_featured: false, status: 'draft' });

  const { data, isLoading } = useQuery({
    queryKey: ['admin-news'],
    queryFn: () => api.get('/news/items/?page_size=100').then(r => r.data).catch(() => api.get('/news/items/?page_size=100').then(r => r.data)),
  });
  const articles: any[] = data?.results ?? [];

  const newsEndpoint = '/news/items/';

  const saveMutation = useMutation({
    mutationFn: (payload: any) =>
      editing
        ? api.patch(`${newsEndpoint}${editing.id}/`, payload).then(r => r.data)
        : api.post(newsEndpoint, payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-news'] });
      setShowForm(false);
      setEditing(null);
      setForm({ title: '', summary: '', body: '', audience: 'all', is_featured: false, status: 'draft' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`${newsEndpoint}${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-news'] }),
  });

  const publishMutation = useMutation({
    mutationFn: (id: number) => api.patch(`${newsEndpoint}${id}/`, { status: 'published' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-news'] }),
  });

  const openEdit = (a: any) => {
    setEditing(a);
    setForm({ title: a.title, summary: a.summary || '', body: a.body || '', audience: a.audience || 'all', is_featured: a.is_featured, status: a.status });
    setShowForm(true);
  };

  const handleDelete = (a: any) => {
    if (window.confirm(`Delete article "${a.title}"?`)) deleteMutation.mutate(a.id);
  };

  const statusBadge = (status: string) => {
    const cls: Record<string, string> = {
      draft:     'bg-yellow-100 text-yellow-700',
      published: 'bg-green-100 text-green-700',
      archived:  'bg-gray-100 text-gray-500',
    };
    return <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full capitalize ${cls[status] ?? 'bg-gray-100 text-gray-500'}`}>{status}</span>;
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-5">
        <div>
          <h2 className="text-lg font-extrabold text-navy-500">News</h2>
          <p className="text-sm text-navy-500/50 mt-0.5">{articles.length} article{articles.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => { setEditing(null); setForm({ title: '', summary: '', body: '', audience: 'all', is_featured: false, status: 'draft' }); setShowForm(v => !v); }}
          className="bg-pink-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-pink-600"
        >
          + New Article
        </button>
      </div>

      {showForm && (
        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 mb-5 space-y-4">
          <h3 className="text-sm font-bold text-navy-500">{editing ? 'Edit Article' : 'New Article'}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className={labelCls}>Title</label>
              <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className={inputCls} placeholder="Article title" />
            </div>
            <div>
              <label className={labelCls}>Audience</label>
              <select value={form.audience} onChange={e => setForm(f => ({ ...f, audience: e.target.value }))} className={inputCls}>
                <option value="all">All</option>
                <option value="scholar">Scholars</option>
                <option value="mentor">Mentors</option>
                <option value="sponsor">Sponsors</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Status</label>
              <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} className={inputCls}>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Summary</label>
              <textarea value={form.summary} onChange={e => setForm(f => ({ ...f, summary: e.target.value }))} rows={2} className={`${inputCls} resize-none`} placeholder="Short summary…" />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Body</label>
              <textarea value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))} rows={10} className={`${inputCls} resize-none`} placeholder="Full article content…" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="news-featured" checked={form.is_featured} onChange={e => setForm(f => ({ ...f, is_featured: e.target.checked }))} className="rounded" />
              <label htmlFor="news-featured" className="text-sm text-navy-500 font-semibold">Featured</label>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={() => saveMutation.mutate(form)} disabled={saveMutation.isPending} className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand">
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
            <button onClick={() => { setShowForm(false); setEditing(null); }} className="text-sm text-navy-500/60 px-4 py-2 rounded-xl border border-gray-200 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {articles.length === 0 ? (
        <p className="text-center py-12 text-sm text-navy-500/40">No articles yet.</p>
      ) : (
        <DataTable headers={['Title', 'Status', 'Audience', 'Featured', 'Published', 'Actions']}>
          {articles.map((a: any) => (
            <tr key={a.id} className="hover:bg-purple-50/30">
              <td className="px-4 py-3 font-semibold text-navy-500 max-w-xs truncate">{a.title}</td>
              <td className="px-4 py-3">{statusBadge(a.status)}</td>
              <td className="px-4 py-3 text-xs text-navy-500/60 capitalize">{a.audience || '—'}</td>
              <td className="px-4 py-3">
                {a.is_featured && <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">Featured</span>}
              </td>
              <td className="px-4 py-3 text-xs text-navy-500/60">
                {a.published_at ? new Date(a.published_at).toLocaleDateString('en-GB') : '—'}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  {a.status === 'draft' && (
                    <button onClick={() => publishMutation.mutate(a.id)} className="text-xs text-green-600 hover:text-green-800 font-semibold">Publish</button>
                  )}
                  <button onClick={() => openEdit(a)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Edit</button>
                  <button onClick={() => handleDelete(a)} className="text-xs text-red-500 hover:text-red-700 font-semibold">Delete</button>
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}

// ── Resources tab ──────────────────────────────────────────────────────────────
function ResourcesTab() {
  const [subTab, setSubTab] = useState<'resources' | 'categories'>('resources');
  const queryClient = useQueryClient();

  // Categories state
  const [showCatForm, setShowCatForm] = useState(false);
  const [editingCat, setEditingCat] = useState<any>(null);
  const [catForm, setCatForm] = useState({ name: '', description: '', parent: '', order: 0 });

  // Resources state
  const [showResForm, setShowResForm] = useState(false);
  const [editingRes, setEditingRes] = useState<any>(null);
  const [resForm, setResForm] = useState({ title: '', description: '', resource_type: 'document', category: '', url: '', audience: 'all' });

  const { data: catsData } = useQuery({
    queryKey: ['admin-resource-categories'],
    queryFn: () => api.get('/resources/categories/?page_size=100').then(r => r.data),
  });
  const categories: any[] = catsData?.results ?? catsData ?? [];

  const { data: resData, isLoading: resLoading } = useQuery({
    queryKey: ['admin-resources'],
    queryFn: () => api.get('/resources/?page_size=100').then(r => r.data),
  });
  const resources: any[] = resData?.results ?? [];

  const saveCatMutation = useMutation({
    mutationFn: (payload: any) =>
      editingCat
        ? api.patch(`/resources/categories/${editingCat.id}/`, payload).then(r => r.data)
        : api.post('/resources/categories/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-resource-categories'] });
      setShowCatForm(false);
      setEditingCat(null);
      setCatForm({ name: '', description: '', parent: '', order: 0 });
    },
  });

  const deleteCatMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/resources/categories/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-resource-categories'] }),
  });

  const saveResMutation = useMutation({
    mutationFn: (payload: any) =>
      editingRes
        ? api.patch(`/resources/${editingRes.id}/`, payload).then(r => r.data)
        : api.post('/resources/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-resources'] });
      setShowResForm(false);
      setEditingRes(null);
      setResForm({ title: '', description: '', resource_type: 'document', category: '', url: '', audience: 'all' });
    },
  });

  const deleteResMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/resources/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-resources'] }),
  });

  const openEditCat = (c: any) => {
    setEditingCat(c);
    setCatForm({ name: c.name, description: c.description || '', parent: c.parent || '', order: c.order || 0 });
    setShowCatForm(true);
  };

  const openEditRes = (r: any) => {
    setEditingRes(r);
    setResForm({ title: r.title, description: r.description || '', resource_type: r.resource_type, category: r.category || '', url: r.url || '', audience: r.audience || 'all' });
    setShowResForm(true);
  };

  const typeBadge = (type: string) => {
    const cls: Record<string, string> = { document: 'bg-blue-100 text-blue-700', link: 'bg-purple-100 text-purple-700', video: 'bg-pink-100 text-pink-700' };
    return <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full capitalize ${cls[type] ?? 'bg-gray-100 text-gray-500'}`}>{type}</span>;
  };

  const saveCatPayload = () => {
    const p: any = { ...catForm };
    if (!p.parent) delete p.parent;
    saveCatMutation.mutate(p);
  };

  const saveResPayload = () => {
    const p: any = { ...resForm };
    if (!p.category) delete p.category;
    saveResMutation.mutate(p);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-5">
        <div>
          <h2 className="text-lg font-extrabold text-navy-500">Resources</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-xl border border-purple-200 overflow-hidden">
            {(['resources', 'categories'] as const).map(s => (
              <button key={s} onClick={() => setSubTab(s)}
                className={`px-3 py-1.5 text-xs font-semibold capitalize transition-all ${subTab === s ? 'bg-gradient-brand-soft text-white' : 'text-navy-500/60 hover:text-navy-500'}`}>
                {s}
              </button>
            ))}
          </div>
          {subTab === 'categories' && (
            <button
              onClick={() => { setEditingCat(null); setCatForm({ name: '', description: '', parent: '', order: 0 }); setShowCatForm(v => !v); }}
              className="bg-pink-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-pink-600"
            >
              + New Category
            </button>
          )}
          {subTab === 'resources' && (
            <button
              onClick={() => { setEditingRes(null); setResForm({ title: '', description: '', resource_type: 'document', category: '', url: '', audience: 'all' }); setShowResForm(v => !v); }}
              className="bg-pink-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-pink-600"
            >
              + New Resource
            </button>
          )}
        </div>
      </div>

      {subTab === 'categories' && (
        <>
          {showCatForm && (
            <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 mb-5 space-y-4">
              <h3 className="text-sm font-bold text-navy-500">{editingCat ? 'Edit Category' : 'New Category'}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Name</label>
                  <input value={catForm.name} onChange={e => setCatForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Category name" />
                </div>
                <div>
                  <label className={labelCls}>Parent Category</label>
                  <select value={catForm.parent} onChange={e => setCatForm(f => ({ ...f, parent: e.target.value }))} className={inputCls}>
                    <option value="">None (top-level)</option>
                    {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Order</label>
                  <input type="number" value={catForm.order} onChange={e => setCatForm(f => ({ ...f, order: parseInt(e.target.value) }))} className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>Description</label>
                  <input value={catForm.description} onChange={e => setCatForm(f => ({ ...f, description: e.target.value }))} className={inputCls} placeholder="Optional…" />
                </div>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <button onClick={saveCatPayload} disabled={saveCatMutation.isPending} className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand">
                  {saveCatMutation.isPending ? 'Saving…' : 'Save'}
                </button>
                <button onClick={() => { setShowCatForm(false); setEditingCat(null); }} className="text-sm text-navy-500/60 px-4 py-2 rounded-xl border border-gray-200 hover:bg-gray-50">Cancel</button>
              </div>
            </div>
          )}
          {categories.length === 0 ? (
            <p className="text-center py-12 text-sm text-navy-500/40">No categories yet.</p>
          ) : (
            <DataTable headers={['Name', 'Parent', 'Resources', 'Actions']}>
              {categories.map((c: any) => (
                <tr key={c.id} className="hover:bg-purple-50/30">
                  <td className="px-4 py-3 font-semibold text-navy-500">{c.name}</td>
                  <td className="px-4 py-3 text-xs text-navy-500/60">{c.parent_name || '—'}</td>
                  <td className="px-4 py-3 text-xs text-navy-500/60">{c.resource_count ?? '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => openEditCat(c)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Edit</button>
                      <button onClick={() => { if (window.confirm(`Delete category "${c.name}"?`)) deleteCatMutation.mutate(c.id); }} className="text-xs text-red-500 hover:text-red-700 font-semibold">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </DataTable>
          )}
        </>
      )}

      {subTab === 'resources' && (
        <>
          {showResForm && (
            <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 mb-5 space-y-4">
              <h3 className="text-sm font-bold text-navy-500">{editingRes ? 'Edit Resource' : 'New Resource'}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className={labelCls}>Title</label>
                  <input value={resForm.title} onChange={e => setResForm(f => ({ ...f, title: e.target.value }))} className={inputCls} placeholder="Resource title" />
                </div>
                <div>
                  <label className={labelCls}>Type</label>
                  <select value={resForm.resource_type} onChange={e => setResForm(f => ({ ...f, resource_type: e.target.value }))} className={inputCls}>
                    <option value="document">Document</option>
                    <option value="link">Link</option>
                    <option value="video">Video</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Category</label>
                  <select value={resForm.category} onChange={e => setResForm(f => ({ ...f, category: e.target.value }))} className={inputCls}>
                    <option value="">No category</option>
                    {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Audience</label>
                  <select value={resForm.audience} onChange={e => setResForm(f => ({ ...f, audience: e.target.value }))} className={inputCls}>
                    <option value="all">All</option>
                    <option value="scholar">Scholars</option>
                    <option value="mentor">Mentors</option>
                    <option value="sponsor">Sponsors</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>URL</label>
                  <input value={resForm.url} onChange={e => setResForm(f => ({ ...f, url: e.target.value }))} className={inputCls} placeholder="https://…" />
                </div>
                <div className="sm:col-span-2">
                  <label className={labelCls}>Description</label>
                  <textarea value={resForm.description} onChange={e => setResForm(f => ({ ...f, description: e.target.value }))} rows={2} className={`${inputCls} resize-none`} placeholder="Optional description…" />
                </div>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <button onClick={saveResPayload} disabled={saveResMutation.isPending} className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand">
                  {saveResMutation.isPending ? 'Saving…' : 'Save'}
                </button>
                <button onClick={() => { setShowResForm(false); setEditingRes(null); }} className="text-sm text-navy-500/60 px-4 py-2 rounded-xl border border-gray-200 hover:bg-gray-50">Cancel</button>
              </div>
            </div>
          )}
          {resLoading ? (
            <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>
          ) : resources.length === 0 ? (
            <p className="text-center py-12 text-sm text-navy-500/40">No resources yet.</p>
          ) : (
            <DataTable headers={['Title', 'Type', 'Category', 'Audience', 'Actions']}>
              {resources.map((r: any) => (
                <tr key={r.id} className="hover:bg-purple-50/30">
                  <td className="px-4 py-3 font-semibold text-navy-500">{r.title}</td>
                  <td className="px-4 py-3">{typeBadge(r.resource_type)}</td>
                  <td className="px-4 py-3 text-xs text-navy-500/60">{r.category_name || '—'}</td>
                  <td className="px-4 py-3 text-xs text-navy-500/60 capitalize">{r.audience || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => openEditRes(r)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Edit</button>
                      <button onClick={() => { if (window.confirm(`Delete resource "${r.title}"?`)) deleteResMutation.mutate(r.id); }} className="text-xs text-red-500 hover:text-red-700 font-semibold">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </DataTable>
          )}
        </>
      )}
    </div>
  );
}

// ── Forums tab ─────────────────────────────────────────────────────────────────
function ForumsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ title: '', description: '', visibility: 'open' });

  const { data, isLoading } = useQuery({
    queryKey: ['admin-forums'],
    queryFn: () => api.get('/forums/forums/?page_size=100').then(r => r.data),
  });
  const forums: any[] = data?.results ?? [];

  const saveMutation = useMutation({
    mutationFn: (payload: any) =>
      editing
        ? api.patch(`/forums/forums/${editing.id}/`, payload).then(r => r.data)
        : api.post('/forums/forums/', payload).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-forums'] });
      setShowForm(false);
      setEditing(null);
      setForm({ title: '', description: '', visibility: 'open' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/forums/forums/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-forums'] }),
  });

  const openEdit = (f: any) => {
    setEditing(f);
    setForm({ title: f.title, description: f.description || '', visibility: f.visibility || 'open' });
    setShowForm(true);
  };

  const handleDelete = (f: any) => {
    if (window.confirm(`Delete forum "${f.title}"?`)) deleteMutation.mutate(f.id);
  };

  const visBadge = (v: string) => {
    const cls: Record<string, string> = { open: 'bg-green-100 text-green-700', programme: 'bg-purple-100 text-purple-700', private: 'bg-gray-100 text-gray-500' };
    return <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full capitalize ${cls[v] ?? 'bg-gray-100 text-gray-500'}`}>{v}</span>;
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-5">
        <div>
          <h2 className="text-lg font-extrabold text-navy-500">Forums</h2>
          <p className="text-sm text-navy-500/50 mt-0.5">{forums.length} forum{forums.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => { setEditing(null); setForm({ title: '', description: '', visibility: 'open' }); setShowForm(v => !v); }}
          className="bg-pink-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-pink-600"
        >
          + New Forum
        </button>
      </div>

      {showForm && (
        <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5 mb-5 space-y-4">
          <h3 className="text-sm font-bold text-navy-500">{editing ? 'Edit Forum' : 'New Forum'}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Title</label>
              <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className={inputCls} placeholder="Forum title" />
            </div>
            <div>
              <label className={labelCls}>Visibility</label>
              <select value={form.visibility} onChange={e => setForm(f => ({ ...f, visibility: e.target.value }))} className={inputCls}>
                <option value="open">Open</option>
                <option value="programme">Programme</option>
                <option value="private">Private</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Description</label>
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className={`${inputCls} resize-none`} placeholder="Optional description…" />
            </div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={() => saveMutation.mutate(form)} disabled={saveMutation.isPending} className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand">
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
            <button onClick={() => { setShowForm(false); setEditing(null); }} className="text-sm text-navy-500/60 px-4 py-2 rounded-xl border border-gray-200 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {forums.length === 0 ? (
        <p className="text-center py-12 text-sm text-navy-500/40">No forums yet.</p>
      ) : (
        <DataTable headers={['Title', 'Visibility', 'Threads', 'Actions']}>
          {forums.map((f: any) => (
            <tr key={f.id} className="hover:bg-purple-50/30">
              <td className="px-4 py-3 font-semibold text-navy-500">{f.title}</td>
              <td className="px-4 py-3">{visBadge(f.visibility)}</td>
              <td className="px-4 py-3 text-xs text-navy-500/60">{f.thread_count ?? '—'}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <button onClick={() => openEdit(f)} className="text-xs text-pink-500 hover:text-pink-700 font-semibold">Edit</button>
                  <button onClick={() => handleDelete(f)} className="text-xs text-red-500 hover:text-red-700 font-semibold">Delete</button>
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}

// ── Settings tab ───────────────────────────────────────────────────────────────
function SettingsTab() {
  const queryClient = useQueryClient();
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['admin-site-settings'],
    queryFn: () => api.get('/cohorts/site-settings/').then(r => r.data),
  });

  const handleSave = async () => {
    if (!logoFile) return;
    setSaving(true);
    setSaved(false);
    try {
      const fd = new FormData();
      fd.append('logo', logoFile);
      await api.patch('/cohorts/site-settings/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      queryClient.invalidateQueries({ queryKey: ['admin-site-settings'] });
      setSaved(true);
      setLogoFile(null);
    } catch {
      // silent fail — user can retry
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h2 className="text-lg font-extrabold text-navy-500">Site Settings</h2>
        <p className="text-sm text-navy-500/50 mt-0.5">Global platform configuration</p>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-6 space-y-5">
        <h3 className="text-sm font-bold text-navy-500">Logo</h3>

        {settings?.logo && (
          <div className="flex items-center gap-4">
            <img src={settings.logo} alt="Current logo" className="max-h-20 rounded-lg border border-purple-100 object-contain" />
            <p className="text-xs text-navy-500/50">Current logo</p>
          </div>
        )}

        <div>
          <label className={labelCls}>Upload new logo</label>
          <input
            type="file"
            accept="image/*"
            onChange={e => setLogoFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm text-navy-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-purple-100 file:text-purple-700 hover:file:bg-purple-200 cursor-pointer"
          />
        </div>

        {saved && (
          <p className="text-xs text-green-600 font-semibold">Logo updated successfully.</p>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSave}
            disabled={!logoFile || saving}
            className="bg-gradient-brand-soft text-white px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 transition-all shadow-brand disabled:opacity-40"
          >
            {saving ? 'Saving…' : 'Save Logo'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page shell ────────────────────────────────────────────────────────────────
export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('dashboard');

  if (user?.role !== 'admin') {
    return (
      <div className="text-center py-24">
        <p className="text-lg font-bold text-navy-500">Access denied</p>
        <p className="text-sm text-navy-500/50 mt-1">Admin access only.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold text-navy-500">Admin Dashboard</h1>
        <p className="text-sm text-navy-500/50 mt-0.5">Platform management &amp; reporting</p>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 mb-6">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              tab === key
                ? 'bg-gradient-brand-soft text-white shadow-brand'
                : 'bg-white text-navy-500/60 shadow-card hover:text-navy-500 hover:shadow-brand'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'dashboard'       && <DashboardTab />}
      {tab === 'contact-report'  && <ContactReportTab />}
      {tab === 'sponsor-updates' && <SponsorUpdateTab />}
      {tab === 'users'           && <UserManagementTab />}
      {tab === 'moderation'      && <ModerationQueueTab />}
      {tab === 'mass-message'    && <MassMessageTab />}
      {tab === 'msg-export'      && <MessagesExportTab />}
      {tab === 'waiting-list'    && <WaitingListTab />}
      {tab === 'sessions'        && <AdminSessionsTab />}
      {tab === 'programmes'      && <ProgrammesTab />}
      {tab === 'cohorts'         && <CohortsTab />}
      {tab === 'news'            && <NewsTab />}
      {tab === 'resources'       && <ResourcesTab />}
      {tab === 'forums'          && <ForumsTab />}
      {tab === 'settings'        && <SettingsTab />}
    </div>
  );
}

// ── Message Export tab ────────────────────────────────────────────────────────
function MessagesExportTab() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo]     = useState('');

  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params: Record<string, string> = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo)   params.date_to   = dateTo;
      const res = await api.get('/messaging/conversations/export/', {
        params,
        responseType: 'blob',
      });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `messages_export${dateFrom || dateTo ? `_${dateFrom || ''}_${dateTo || ''}` : ''}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h2 className="text-lg font-extrabold text-navy-500">Message Export</h2>
        <p className="text-sm text-navy-500/50 mt-0.5">
          Download all platform messages as a CSV file for review or compliance purposes.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>From date <span className="font-normal text-navy-500/40 normal-case">(optional)</span></label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className={inputCls}
            />
          </div>
          <div>
            <label className={labelCls}>To date <span className="font-normal text-navy-500/40 normal-case">(optional)</span></label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>

        <div className="pt-1 flex items-center gap-4">
          <button
            onClick={handleExport}
            disabled={exporting}
            className="inline-flex items-center gap-2 bg-gradient-brand-soft text-white px-6 py-2.5 rounded-xl text-sm font-bold hover:opacity-90 disabled:opacity-50 transition-all shadow-brand"
          >
            {exporting ? (
              <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Exporting…</>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download CSV
              </>
            )}
          </button>
          {(dateFrom || dateTo) && (
            <button
              onClick={() => { setDateFrom(''); setDateTo(''); }}
              className="text-xs text-navy-500/40 hover:text-navy-500 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="border-t border-purple-50 pt-4">
          <p className="text-xs text-navy-500/40">
            The export includes all delivered, flagged, and pending messages.
            Each row contains: date, conversation ID, subject, type, sender, message body, status, and participants.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard tab ─────────────────────────────────────────────────────────────
function DashboardTab() {
  const { data: users }    = useQuery({ queryKey: ['admin-users'],    queryFn: () => api.get('/users/?page_size=200').then(r => r.data) });
  const { data: sessions } = useQuery({ queryKey: ['admin-sessions'], queryFn: () => api.get('/sessions/sessions/?page_size=200').then(r => r.data) });
  const { data: goals }    = useQuery({ queryKey: ['admin-goals'],    queryFn: () => api.get('/goals/goals/?page_size=200').then(r => r.data) });
  const { data: waiting }  = useQuery({ queryKey: ['admin-waiting'],  queryFn: () => api.get('/users/waiting-list/?is_matched=false').then(r => r.data) });

  const userList: any[] = users?.results ?? [];
  const sessionList: any[] = sessions?.results ?? [];
  const goalList: any[] = goals?.results ?? [];

  const roleCount = (role: string) => userList.filter((u: any) => u.role === role).length;
  const sessionsByStatus = (s: string) => sessionList.filter((x: any) => x.status === s).length;

  const kpis = [
    { label: 'Total Users',       value: users?.count    ?? '—', sub: 'on platform',         accent: true  },
    { label: 'Active Sessions',   value: sessionsByStatus('confirmed'), sub: 'confirmed upcoming' },
    { label: 'Active Goals',      value: goalList.filter((g: any) => g.status === 'active').length, sub: 'in progress' },
    { label: 'Waiting List',      value: waiting?.count  ?? '—', sub: 'unmatched scholars'   },
    { label: 'Scholars',          value: roleCount('scholar'),   sub: 'on platform'           },
    { label: 'Mentors',           value: roleCount('mentor'),    sub: 'on platform'           },
    { label: 'Sessions Complete', value: sessionsByStatus('completed'), sub: 'all time'       },
    { label: 'Goals Completed',   value: goalList.filter((g: any) => g.status === 'completed').length, sub: 'all time' },
  ];

  // Simple bar chart using CSS
  const sessionPhases = [
    { label: 'Pending',   count: sessionsByStatus('pending'),   colour: 'bg-yellow-400' },
    { label: 'Confirmed', count: sessionsByStatus('confirmed'), colour: 'bg-green-400'  },
    { label: 'Completed', count: sessionsByStatus('completed'), colour: 'bg-purple-400' },
    { label: 'Cancelled', count: sessionsByStatus('cancelled'), colour: 'bg-red-400'    },
  ];
  const maxSessions = Math.max(...sessionPhases.map(s => s.count), 1);

  const goalCategories = ['career','technical','personal','academic','networking','other'];
  const goalCatCounts = goalCategories.map(c => ({
    label: c, count: goalList.filter((g: any) => g.category === c).length,
  }));
  const maxGoals = Math.max(...goalCatCounts.map(g => g.count), 1);

  return (
    <div className="space-y-8">
      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map(k => (
          <div key={k.label} className={`rounded-2xl p-5 shadow-card ${k.accent ? 'bg-gradient-brand-soft text-white shadow-brand' : 'bg-white'}`}>
            <p className={`text-[10px] font-semibold uppercase tracking-wider ${k.accent ? 'text-white/70' : 'text-navy-500/40'}`}>{k.label}</p>
            <p className={`text-2xl font-extrabold mt-1 ${k.accent ? 'text-white' : 'text-navy-500'}`}>{k.value}</p>
            <p className={`text-[10px] mt-0.5 ${k.accent ? 'text-white/60' : 'text-navy-500/40'}`}>{k.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sessions by status bar chart */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h3 className="text-sm font-bold text-navy-500 mb-4">Sessions by Status</h3>
          <div className="space-y-3">
            {sessionPhases.map(phase => (
              <div key={phase.label} className="flex items-center gap-3">
                <span className="text-xs text-navy-500/50 w-20 capitalize">{phase.label}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div className={`${phase.colour} h-4 rounded-full transition-all`}
                    style={{ width: `${(phase.count / maxSessions) * 100}%` }} />
                </div>
                <span className="text-xs font-bold text-navy-500 w-6 text-right">{phase.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Goals by category */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h3 className="text-sm font-bold text-navy-500 mb-4">Goals by Category</h3>
          <div className="space-y-3">
            {goalCatCounts.map(cat => (
              <div key={cat.label} className="flex items-center gap-3">
                <span className="text-xs text-navy-500/50 w-20 capitalize">{cat.label}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div className="bg-gradient-brand-soft h-4 rounded-full transition-all"
                    style={{ width: `${(cat.count / maxGoals) * 100}%` }} />
                </div>
                <span className="text-xs font-bold text-navy-500 w-6 text-right">{cat.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* User role breakdown */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h3 className="text-sm font-bold text-navy-500 mb-4">Users by Role</h3>
          <div className="space-y-3">
            {['scholar','mentor','sponsor','alumni','admin'].map(role => {
              const count = roleCount(role);
              const pct = userList.length ? (count / userList.length) * 100 : 0;
              return (
                <div key={role} className="flex items-center gap-3">
                  <span className="text-xs text-navy-500/50 w-20 capitalize">{role}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                    <div className="bg-pink-500 h-4 rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs font-bold text-navy-500 w-6 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Goal status breakdown */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <h3 className="text-sm font-bold text-navy-500 mb-4">Goal Status</h3>
          <div className="space-y-3">
            {['active','completed','paused'].map(status => {
              const count = goalList.filter((g: any) => g.status === status).length;
              const pct = goalList.length ? (count / goalList.length) * 100 : 0;
              const colours: Record<string,string> = { active: 'bg-green-400', completed: 'bg-purple-400', paused: 'bg-yellow-400' };
              return (
                <div key={status} className="flex items-center gap-3">
                  <span className="text-xs text-navy-500/50 w-20 capitalize">{status}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                    <div className={`${colours[status]} h-4 rounded-full transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs font-bold text-navy-500 w-6 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Waiting list tab ──────────────────────────────────────────────────────────
function WaitingListTab() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['waiting-list-admin'],
    queryFn: () => api.get('/users/waiting-list/').then(r => r.data),
  });

  const matchEntry = useMutation({
    mutationFn: (id: number) => api.post(`/users/waiting-list/${id}/match/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['waiting-list-admin'] }),
  });

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div>
      <SectionHeader title="Mentor Waiting List" sub="Scholars awaiting mentor assignment" />
      {!data?.results?.length ? (
        <p className="text-center py-12 text-sm text-navy-500/40">No scholars on the waiting list.</p>
      ) : (
        <DataTable headers={['Scholar', 'Discipline', 'Preferred Mentor', 'Requested', 'Status', 'Actions']}>
          {data.results.map((e: any) => (
            <tr key={e.id} className="hover:bg-purple-50/30">
              <td className="px-4 py-3 text-sm font-medium text-navy-500">{e.scholar_name}</td>
              <td className="px-4 py-3 text-xs text-navy-500/60">{e.engineering_discipline || '—'}</td>
              <td className="px-4 py-3 text-xs text-navy-500/60">{e.preferred_mentor_name || 'Any'}</td>
              <td className="px-4 py-3 text-xs text-navy-500/40">{new Date(e.requested_at).toLocaleDateString('en-GB')}</td>
              <td className="px-4 py-3">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${e.is_matched ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                  {e.is_matched ? 'Matched' : 'Waiting'}
                </span>
              </td>
              <td className="px-4 py-3">
                {!e.is_matched && (
                  <button onClick={() => matchEntry.mutate(e.id)}
                    className="text-xs font-semibold text-pink-500 hover:underline">
                    Mark matched
                  </button>
                )}
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}

// ── Sessions admin tab ────────────────────────────────────────────────────────
function AdminSessionsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-sessions-tab'],
    queryFn: () => api.get('/sessions/sessions/?page_size=50').then(r => r.data),
  });

  const statusColour: Record<string, string> = {
    pending:   'bg-yellow-100 text-yellow-700',
    confirmed: 'bg-green-100  text-green-700',
    cancelled: 'bg-red-100    text-red-500',
    completed: 'bg-purple-100 text-purple-700',
    no_show:   'bg-gray-100   text-gray-500',
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="w-7 h-7 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;

  return (
    <div>
      <SectionHeader title="All Mentoring Sessions" sub="Overview of every session on the platform" />
      {!data?.results?.length ? (
        <p className="text-center py-12 text-sm text-navy-500/40">No sessions recorded yet.</p>
      ) : (
        <DataTable headers={['Scholar', 'Mentor', 'Title', 'Date', 'Status']}>
          {data.results.map((s: any) => (
            <tr key={s.id} className="hover:bg-purple-50/30">
              <td className="px-4 py-3 text-sm font-medium text-navy-500">{s.scholar_name}</td>
              <td className="px-4 py-3 text-xs text-navy-500/60">{s.mentor_name}</td>
              <td className="px-4 py-3 text-xs text-navy-500/60">{s.title}</td>
              <td className="px-4 py-3 text-xs text-navy-500/40">{new Date(s.start_time).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
              <td className="px-4 py-3">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full capitalize ${statusColour[s.status] ?? ''}`}>
                  {s.status.replace('_', ' ')}
                </span>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  );
}
