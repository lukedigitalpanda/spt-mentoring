import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { NewsItem, PaginatedResponse } from '../types';

// ── Decorative brand star (matches logo style) ──────────────────────────────
function BrandStar({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

// ── Welcome hero ─────────────────────────────────────────────────────────────
function Hero({ name, role }: { name: string; role: string }) {
  const greetings: Record<string, string> = {
    scholar: 'Your engineering future starts here.',
    mentor:  'Thank you for inspiring the next generation.',
    sponsor: 'Your investment is shaping future engineers.',
    alumni:  'Welcome back – keep inspiring others.',
    admin:   'Platform overview at a glance.',
  };
  return (
    <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-10 mb-8 shadow-brand">
      {/* Decorative blobs */}
      <div className="absolute -top-8 -right-8 w-56 h-56 rounded-full bg-white/5" />
      <div className="absolute bottom-0 right-24 w-32 h-32 rounded-full bg-pink-DEFAULT/20 blur-2xl" />
      <div className="relative z-10">
        <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1 capitalize">{role}</p>
        <h1 className="text-3xl font-extrabold">
          Welcome back, <span className="text-pink-200">{name}</span>
        </h1>
        <p className="mt-2 text-white/70 text-sm">{greetings[role] ?? ''}</p>
      </div>
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({
  label, value, sub, accent = false,
}: { label: string; value: string | number; sub?: string; accent?: boolean }) {
  return (
    <div className={`rounded-2xl p-5 shadow-card ${accent ? 'bg-gradient-brand-soft text-white shadow-brand' : 'bg-white'}`}>
      <p className={`text-xs font-semibold uppercase tracking-wider ${accent ? 'text-white/70' : 'text-navy-DEFAULT/40'}`}>{label}</p>
      <p className={`mt-1.5 text-2xl font-extrabold ${accent ? 'text-white' : 'text-navy-DEFAULT'}`}>{value}</p>
      {sub && <p className={`mt-1 text-xs ${accent ? 'text-white/60' : 'text-navy-DEFAULT/40'}`}>{sub}</p>}
    </div>
  );
}

// ── Quick action card ─────────────────────────────────────────────────────────
function ActionCard({
  to, icon, label, sub, color,
}: { to: string; icon: React.ReactNode; label: string; sub: string; color: string }) {
  return (
    <Link to={to} className="group bg-white rounded-2xl shadow-card hover:shadow-brand transition-all p-6 flex flex-col items-start">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 transition-all ${color}`}>
        {icon}
      </div>
      <h3 className="font-bold text-navy-DEFAULT text-sm group-hover:text-pink-DEFAULT transition-colors">{label}</h3>
      <p className="text-xs text-navy-DEFAULT/50 mt-0.5">{sub}</p>
      <div className="mt-auto pt-4 flex items-center text-xs font-semibold text-pink-DEFAULT">
        Open <svg className="w-3.5 h-3.5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" /></svg>
      </div>
    </Link>
  );
}

// ── Featured news banner ──────────────────────────────────────────────────────
function FeaturedNewsBanner({ item }: { item: NewsItem }) {
  return (
    <Link to={`/news/${item.id}`} className="group relative rounded-2xl overflow-hidden block mb-8">
      <div className="bg-gradient-brand p-8 md:p-10">
        {item.cover_image && (
          <img src={item.cover_image} alt="" className="absolute inset-0 w-full h-full object-cover opacity-10" />
        )}
        <div className="relative z-10 max-w-xl">
          <div className="flex items-center gap-2 mb-3">
            <BrandStar size={16} />
            <span className="text-xs font-semibold text-pink-200 uppercase tracking-wider">Featured News</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white leading-snug group-hover:text-pink-200 transition-colors">
            {item.title}
          </h2>
          <p className="mt-2 text-white/60 text-sm line-clamp-2">{item.summary}</p>
          <span className="mt-5 inline-flex items-center gap-2 bg-pink-DEFAULT text-white text-xs font-bold px-4 py-2 rounded-lg group-hover:bg-pink-600 transition-colors">
            Read more
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function HomePage() {
  const { user } = useAuth();

  const { data: news } = useQuery<PaginatedResponse<NewsItem>>({
    queryKey: ['news', 'featured'],
    queryFn: () => api.get('/news/items/?is_featured=true&status=published').then(r => r.data),
  });

  const { data: activity } = useQuery({
    queryKey: ['activity', user?.id],
    queryFn: () => user ? api.get(`/users/${user.id}/activity_summary/`).then(r => r.data) : null,
    enabled: !!user,
  });

  const featured = news?.results?.[0];
  const fmt = (d?: string | null) => d ? new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '—';

  return (
    <div className="space-y-8">
      {/* Hero */}
      <Hero name={user?.first_name ?? ''} role={user?.role ?? ''} />

      {/* Featured news */}
      {featured && <FeaturedNewsBanner item={featured} />}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Last message sent"     value={fmt(activity?.last_message_sent)}     sub="by you"          accent />
        <StatCard label="Last message received" value={fmt(activity?.last_message_received)} sub="from your network" />
        <StatCard label="Unread messages"       value="—" sub="Check messages" />
        <StatCard label="New resources"         value="—" sub="Check resources" />
      </div>

      {/* Quick actions */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BrandStar size={16} />
          <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Quick access</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <ActionCard
            to="/messages"
            color="bg-purple-50 group-hover:bg-purple-100"
            label="Messages"
            sub="Chat with your mentor or scholar"
            icon={<svg className="w-5 h-5 text-purple-DEFAULT" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>}
          />
          <ActionCard
            to="/forums"
            color="bg-pink-50 group-hover:bg-pink-100"
            label="Forums"
            sub="Community discussions & group mentoring"
            icon={<svg className="w-5 h-5 text-pink-DEFAULT" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" /></svg>}
          />
          <ActionCard
            to="/resources"
            color="bg-orange-50 group-hover:bg-orange-100"
            label="Resources"
            sub="Documents, links & guides"
            icon={<svg className="w-5 h-5 text-orange-DEFAULT" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
          />
          <ActionCard
            to="/surveys"
            color="bg-navy-50 group-hover:bg-navy-100"
            label="Surveys"
            sub="Track your progress & skills"
            icon={<svg className="w-5 h-5 text-navy-DEFAULT" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
          />
          <ActionCard
            to="/news"
            color="bg-purple-50 group-hover:bg-purple-100"
            label="News"
            sub="Latest from the programme"
            icon={<svg className="w-5 h-5 text-purple-DEFAULT" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>}
          />
          <ActionCard
            to="/profile"
            color="bg-pink-50 group-hover:bg-pink-100"
            label="My Profile"
            sub="Edit your details & goals"
            icon={<svg className="w-5 h-5 text-pink-DEFAULT" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
        </div>
      </div>

      {/* Recent news list */}
      {news && news.results.length > 1 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BrandStar size={16} />
              <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Latest News</h2>
            </div>
            <Link to="/news" className="text-xs font-semibold text-pink-DEFAULT hover:underline flex items-center gap-1">
              View all
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" /></svg>
            </Link>
          </div>
          <div className="space-y-2">
            {news.results.slice(1, 5).map(item => (
              <Link
                key={item.id}
                to={`/news/${item.id}`}
                className="flex items-start justify-between bg-white rounded-xl shadow-card hover:shadow-brand transition-all p-4 group"
              >
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sm text-navy-DEFAULT group-hover:text-pink-DEFAULT transition-colors truncate">
                    {item.title}
                  </h3>
                  <p className="text-xs text-navy-DEFAULT/50 mt-0.5 line-clamp-1">{item.summary}</p>
                </div>
                <span className="ml-4 text-xs text-navy-DEFAULT/30 whitespace-nowrap flex-shrink-0 pt-0.5">
                  {item.published_at ? new Date(item.published_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
