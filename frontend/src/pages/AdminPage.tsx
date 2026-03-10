import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';

type Tab = 'contact-report' | 'sponsor-updates' | 'users' | 'moderation' | 'mass-message';

const tabs: [Tab, string][] = [
  ['contact-report',  'Contact Report'],
  ['sponsor-updates', 'Sponsor Updates'],
  ['users',           'User Management'],
  ['moderation',      'Moderation Queue'],
  ['mass-message',    'Mass Message'],
];

// ── Shared helpers ────────────────────────────────────────────────────────────
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function SectionHeader({ title, sub, csvHref }: { title: string; sub?: string; csvHref?: string }) {
  return (
    <div className="flex justify-between items-start mb-5">
      <div>
        <h2 className="text-lg font-extrabold text-navy-DEFAULT">{title}</h2>
        {sub && <p className="text-sm text-navy-DEFAULT/50 mt-0.5">{sub}</p>}
      </div>
      {csvHref && (
        <a href={csvHref}
          className="inline-flex items-center gap-1.5 border-2 border-purple-200 text-purple-DEFAULT text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-purple-50 transition-colors"
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
    <div className="bg-white rounded-2xl shadow-card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gradient-brand-pale">
            {headers.map(h => (
              <th key={h} className="text-left px-4 py-3 text-xs font-bold text-navy-DEFAULT uppercase tracking-wider">{h}</th>
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
  if (isLoading) return <p className="text-navy-DEFAULT/40 text-sm">Loading…</p>;
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
              <p className="font-semibold text-navy-DEFAULT">{row.scholar_name}</p>
              <p className="text-[11px] text-navy-DEFAULT/40">{row.scholar_email}</p>
            </td>
            <td className="px-4 py-3">
              <p className="font-semibold text-navy-DEFAULT">{row.mentor_name}</p>
              <p className="text-[11px] text-navy-DEFAULT/40">{row.mentor_email}</p>
            </td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">
              {row.scholar_last_message ? new Date(row.scholar_last_message).toLocaleDateString('en-GB') : 'Never'}
            </td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">
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
  if (isLoading) return <p className="text-navy-DEFAULT/40 text-sm">Loading…</p>;
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
            <td className="px-4 py-3 font-semibold text-navy-DEFAULT">{row.scholar_name}</td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">{row.sponsor_name || '—'}</td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">
              {row.last_update_sent ? new Date(row.last_update_sent).toLocaleDateString('en-GB') : 'Never'}
            </td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">{row.days_since_update ?? '—'}</td>
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
          <h2 className="text-lg font-extrabold text-navy-DEFAULT">User Management</h2>
          <p className="text-sm text-navy-DEFAULT/50 mt-0.5">{data?.count ?? '…'} users</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name, email, CRM ID…"
            className="border-2 border-purple-100 rounded-xl px-3 py-1.5 text-sm text-navy-DEFAULT focus:outline-none focus:border-pink-DEFAULT transition-colors w-64"
          />
          <a href={`${API}/users/export/`}
            className="inline-flex items-center gap-1.5 border-2 border-purple-200 text-purple-DEFAULT text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-purple-50"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
            Export CSV
          </a>
        </div>
      </div>
      <DataTable headers={['Name', 'Email', 'Role', 'Location', 'Status']}>
        {data?.results?.map((u: any) => (
          <tr key={u.id}>
            <td className="px-4 py-3 font-semibold text-navy-DEFAULT">{u.full_name}</td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">{u.email}</td>
            <td className="px-4 py-3">
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full capitalize ${roleColour[u.role] || 'bg-gray-100 text-gray-600'}`}>
                {u.role}
              </span>
            </td>
            <td className="px-4 py-3 text-navy-DEFAULT/60">{u.location || '—'}</td>
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
        <h2 className="text-lg font-extrabold text-navy-DEFAULT">Moderation Queue</h2>
        {data?.length > 0 && (
          <span className="bg-pink-DEFAULT text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {data.length}
          </span>
        )}
      </div>
      {(!data || data.length === 0) ? (
        <div className="text-center py-16 bg-white rounded-2xl shadow-card text-navy-DEFAULT/30">
          <svg className="w-10 h-10 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <p className="font-semibold text-sm">All clear – no flagged messages</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((msg: any) => (
            <div key={msg.id} className="bg-white rounded-2xl shadow-card border-l-4 border-orange-DEFAULT p-5">
              <div className="flex justify-between items-start gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-orange-DEFAULT uppercase tracking-wider mb-1">{msg.moderation_note}</p>
                  <p className="font-semibold text-navy-DEFAULT text-sm">{msg.sender_name}</p>
                  <p className="text-sm text-navy-DEFAULT/70 mt-1 line-clamp-3">{msg.body}</p>
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
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sendFromEmail, setSendFromEmail] = useState('mentoring@smallpeice.co.uk');
  const [roles, setRoles] = useState<string[]>([]);
  const [statusMsg, setStatusMsg] = useState('');

  const sendMassMessage = async () => {
    if (!subject || !body) return;
    const { data } = await api.post('/messaging/mass-messages/', {
      subject, body, recipient_roles: roles, send_from_email: sendFromEmail,
    });
    await api.post(`/messaging/mass-messages/${data.id}/send/`);
    setStatusMsg('Message queued for delivery!');
    setSubject(''); setBody('');
  };

  const inputCls = "w-full border-2 border-purple-100 rounded-xl px-4 py-2.5 text-sm text-navy-DEFAULT bg-white focus:outline-none focus:border-pink-DEFAULT transition-colors";
  const labelCls = "block text-xs font-bold text-navy-DEFAULT uppercase tracking-wider mb-1.5";

  return (
    <div className="max-w-2xl">
      <div className="mb-5">
        <h2 className="text-lg font-extrabold text-navy-DEFAULT">Send Mass Message</h2>
        <p className="text-sm text-navy-DEFAULT/50 mt-0.5">Reach all scholars, mentors or sponsors at once.</p>
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6 space-y-5">
        <div>
          <label className={labelCls}>Send from</label>
          <select value={sendFromEmail} onChange={e => setSendFromEmail(e.target.value)} className={inputCls}>
            <option value="mentoring@smallpeice.co.uk">mentoring@smallpeice.co.uk</option>
            <option value="scholarships@smallpeice.co.uk">scholarships@smallpeice.co.uk</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>Recipients</label>
          <div className="flex flex-wrap gap-3">
            {['scholar', 'mentor', 'sponsor', 'alumni'].map(role => (
              <label key={role} className="flex items-center gap-2 text-sm font-medium text-navy-DEFAULT cursor-pointer">
                <input
                  type="checkbox"
                  checked={roles.includes(role)}
                  onChange={e => setRoles(prev => e.target.checked ? [...prev, role] : prev.filter(r => r !== role))}
                  className="w-4 h-4 rounded accent-pink-DEFAULT"
                />
                <span className="capitalize">{role}s</span>
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className={labelCls}>Subject</label>
          <input value={subject} onChange={e => setSubject(e.target.value)} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Message body</label>
          <textarea value={body} onChange={e => setBody(e.target.value)} rows={6} className={inputCls} />
        </div>
        {statusMsg && (
          <div className="bg-purple-50 border border-purple-200 text-purple-700 text-sm font-semibold px-4 py-3 rounded-xl flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
            {statusMsg}
          </div>
        )}
        <button
          onClick={sendMassMessage}
          disabled={!subject || !body || roles.length === 0}
          className="bg-gradient-brand-soft text-white px-6 py-2.5 rounded-xl text-sm font-bold hover:opacity-90 disabled:opacity-40 transition-all shadow-brand flex items-center gap-2"
        >
          Send Mass Message
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
        </button>
      </div>
    </div>
  );
}

// ── Page shell ────────────────────────────────────────────────────────────────
export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('contact-report');

  if (user?.role !== 'admin') {
    return (
      <div className="text-center py-24">
        <p className="text-lg font-bold text-navy-DEFAULT">Access denied</p>
        <p className="text-sm text-navy-DEFAULT/50 mt-1">Admin access only.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold text-navy-DEFAULT">Admin Dashboard</h1>
        <p className="text-sm text-navy-DEFAULT/50 mt-0.5">Platform management &amp; reporting</p>
      </div>

      {/* Tab bar */}
      <div className="bg-white rounded-2xl shadow-card p-1.5 inline-flex gap-1 mb-6">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
              tab === key
                ? 'bg-gradient-brand-soft text-white shadow-brand'
                : 'text-navy-DEFAULT/60 hover:text-navy-DEFAULT hover:bg-purple-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'contact-report'  && <ContactReportTab />}
      {tab === 'sponsor-updates' && <SponsorUpdateTab />}
      {tab === 'users'           && <UserManagementTab />}
      {tab === 'moderation'      && <ModerationQueueTab />}
      {tab === 'mass-message'    && <MassMessageTab />}
    </div>
  );
}
