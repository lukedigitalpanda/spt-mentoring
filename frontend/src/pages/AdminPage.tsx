import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';

type Tab = 'users' | 'contact-report' | 'sponsor-updates' | 'moderation' | 'mass-message';

export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('contact-report');

  if (user?.role !== 'admin') {
    return <div className="text-center py-20 text-gray-500">Access denied.</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Admin Dashboard</h1>

      {/* Tab nav */}
      <div className="flex space-x-1 border-b border-gray-200 mb-6">
        {([
          ['contact-report', 'Contact Report'],
          ['sponsor-updates', 'Sponsor Updates'],
          ['users', 'User Management'],
          ['moderation', 'Moderation Queue'],
          ['mass-message', 'Mass Message'],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'contact-report' && <ContactReportTab />}
      {tab === 'sponsor-updates' && <SponsorUpdateTab />}
      {tab === 'users' && <UserManagementTab />}
      {tab === 'moderation' && <ModerationQueueTab />}
      {tab === 'mass-message' && <MassMessageTab />}
    </div>
  );
}

function ContactReportTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-contact'],
    queryFn: () => api.get('/reports/contact/').then(r => r.data),
  });

  if (isLoading) return <div className="text-gray-500">Loading…</div>;

  const overdue = data?.results?.filter((r: any) => r.needs_chase) || [];

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-lg font-semibold">Scholar / Mentor Contact Report</h2>
          <p className="text-sm text-gray-500 mt-1">
            {overdue.length} pairs need chasing (no contact in {data?.threshold_days} days)
          </p>
        </div>
        <a
          href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/reports/contact/?format=csv`}
          className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
        >
          Export CSV
        </a>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Scholar</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Mentor</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Last Scholar msg</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Last Mentor msg</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.results?.map((row: any) => (
              <tr key={`${row.scholar_id}-${row.mentor_id}`} className={row.needs_chase ? 'bg-red-50' : ''}>
                <td className="px-4 py-3">
                  <div>{row.scholar_name}</div>
                  <div className="text-xs text-gray-400">{row.scholar_email}</div>
                </td>
                <td className="px-4 py-3">
                  <div>{row.mentor_name}</div>
                  <div className="text-xs text-gray-400">{row.mentor_email}</div>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {row.scholar_last_message ? new Date(row.scholar_last_message).toLocaleDateString('en-GB') : 'Never'}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {row.mentor_last_message ? new Date(row.mentor_last_message).toLocaleDateString('en-GB') : 'Never'}
                </td>
                <td className="px-4 py-3">
                  {row.needs_chase ? (
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Needs chasing</span>
                  ) : (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Active</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SponsorUpdateTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-sponsor'],
    queryFn: () => api.get('/reports/sponsor-updates/').then(r => r.data),
  });

  if (isLoading) return <div className="text-gray-500">Loading…</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Sponsor Update Report</h2>
        <a
          href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/reports/sponsor-updates/?format=csv`}
          className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
        >
          Export CSV
        </a>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Scholar</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Sponsor</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Last Update</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Days Since</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.results?.map((row: any) => (
              <tr key={row.scholar_id} className={row.is_overdue ? 'bg-amber-50' : ''}>
                <td className="px-4 py-3">{row.scholar_name}</td>
                <td className="px-4 py-3">{row.sponsor_name || '—'}</td>
                <td className="px-4 py-3">{row.last_update_sent ? new Date(row.last_update_sent).toLocaleDateString('en-GB') : 'Never'}</td>
                <td className="px-4 py-3">{row.days_since_update ?? '—'}</td>
                <td className="px-4 py-3">
                  {row.is_overdue ? (
                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Overdue</span>
                  ) : (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Up to date</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UserManagementTab() {
  const [search, setSearch] = useState('');
  const { data } = useQuery({
    queryKey: ['admin-users', search],
    queryFn: () => api.get(`/users/?search=${search}`).then(r => r.data),
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">User Management</h2>
        <div className="flex space-x-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search users…"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/users/export/`}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
          >
            Export CSV
          </a>
        </div>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Name</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Email</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Role</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Location</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.results?.map((u: any) => (
              <tr key={u.id}>
                <td className="px-4 py-3 font-medium">{u.full_name}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3 capitalize">{u.role}</td>
                <td className="px-4 py-3 text-gray-600">{u.location || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ModerationQueueTab() {
  const { data, refetch } = useQuery({
    queryKey: ['flagged-messages'],
    queryFn: () => api.get('/moderation/flagged-messages/').then(r => r.data),
  });

  const approve = async (id: number) => {
    await api.post(`/moderation/flagged-messages/${id}/approve/`);
    refetch();
  };
  const reject = async (id: number) => {
    await api.post(`/moderation/flagged-messages/${id}/reject/`);
    refetch();
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">
        Moderation Queue
        {data?.length > 0 && (
          <span className="ml-2 bg-red-100 text-red-700 text-sm px-2 py-0.5 rounded-full">{data.length}</span>
        )}
      </h2>
      {(!data || data.length === 0) ? (
        <div className="text-center py-12 text-gray-400 bg-white rounded-lg border border-gray-200">
          No flagged messages to review.
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((msg: any) => (
            <div key={msg.id} className="bg-white rounded-lg border border-amber-200 p-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-sm font-medium text-gray-900">{msg.sender_name}</p>
                  <p className="text-sm text-gray-700 mt-1">{msg.body}</p>
                  <p className="text-xs text-amber-600 mt-2">{msg.moderation_note}</p>
                </div>
                <div className="flex space-x-2 ml-4">
                  <button
                    onClick={() => approve(msg.id)}
                    className="text-xs bg-green-100 text-green-700 px-3 py-1.5 rounded-md hover:bg-green-200"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => reject(msg.id)}
                    className="text-xs bg-red-100 text-red-700 px-3 py-1.5 rounded-md hover:bg-red-200"
                  >
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
  const [sendFromEmail, setSendFromEmail] = useState('mentoring@spt.org');
  const [roles, setRoles] = useState<string[]>([]);
  const [status, setStatus] = useState('');

  const sendMassMessage = async () => {
    if (!subject || !body) return;
    const { data } = await api.post('/messaging/mass-messages/', {
      subject, body, recipient_roles: roles, send_from_email: sendFromEmail,
    });
    await api.post(`/messaging/mass-messages/${data.id}/send/`);
    setStatus('Message queued for delivery!');
    setSubject(''); setBody('');
  };

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold mb-4">Send Mass Message</h2>
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Send from</label>
          <select
            value={sendFromEmail}
            onChange={e => setSendFromEmail(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="mentoring@spt.org">mentoring@spt.org</option>
            <option value="scholarships@spt.org">scholarships@spt.org</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Recipients</label>
          <div className="flex flex-wrap gap-2">
            {['scholar', 'mentor', 'sponsor', 'alumni'].map(role => (
              <label key={role} className="flex items-center space-x-2 text-sm">
                <input
                  type="checkbox"
                  checked={roles.includes(role)}
                  onChange={e => setRoles(prev => e.target.checked ? [...prev, role] : prev.filter(r => r !== role))}
                />
                <span className="capitalize">{role}s</span>
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
          <input
            value={subject}
            onChange={e => setSubject(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
          <textarea
            value={body}
            onChange={e => setBody(e.target.value)}
            rows={6}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        {status && <div className="bg-green-50 border border-green-200 text-green-700 px-3 py-2 rounded-lg text-sm">{status}</div>}
        <button
          onClick={sendMassMessage}
          disabled={!subject || !body}
          className="bg-blue-700 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 disabled:opacity-50"
        >
          Send Mass Message
        </button>
      </div>
    </div>
  );
}
