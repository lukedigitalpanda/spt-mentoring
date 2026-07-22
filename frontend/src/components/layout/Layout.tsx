import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../hooks/useAuth';
import { usePushNotifications } from '../../hooks/usePushNotifications';
import BrandLogo from '../ui/BrandLogo';
import api from '../../utils/api';
import { userHasRole } from '../../utils/roles';

const navItems = [
  { path: '/',           label: 'Home',             roles: ['scholar','mentor','sponsor','alumni'] },
  { path: '/messages',   label: 'Messages',         roles: ['scholar','mentor','sponsor','alumni'] },
  { path: '/sessions',   label: 'Sessions',         roles: ['scholar','mentor','alumni'] },
  { path: '/goals',      label: 'Goals',            roles: ['scholar','mentor','alumni'] },
  { path: '/mentors',    label: 'Find a Mentor',    roles: ['scholar','alumni'] },
  { path: '/forums',     label: 'Forums',           roles: ['scholar','mentor','alumni'] },
  { path: '/resources',  label: 'Resources',        roles: ['scholar','mentor','sponsor','alumni'] },
  { path: '/surveys',    label: 'Surveys',          roles: ['scholar','mentor','alumni'] },
  { path: '/news',       label: 'News',             roles: ['scholar','mentor','sponsor','alumni'] },
  { path: '/admin',      label: 'Admin',            roles: ['admin'] },
];

const roleBadgeStyle: Record<string, string> = {
  scholar:  'bg-purple-100 text-purple-700',
  mentor:   'bg-navy-100  text-navy-700',
  sponsor:  'bg-orange-100 text-orange-700',
  alumni:   'bg-pink-100  text-pink-700',
  admin:    'bg-gradient-brand-soft text-white',
};

function NotificationBell() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { data } = useQuery<{ count: number }>({
    queryKey: ['notification-count'],
    queryFn: () => api.get('/notifications/unread_count/').then(r => r.data),
    enabled: isAuthenticated,
    refetchInterval: 30_000,
  });
  const count = data?.count ?? 0;
  return (
    <button onClick={() => navigate('/notifications')}
      className="relative p-1.5 text-navy-500/50 hover:text-navy-500 transition-colors">
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-pink-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  );
}

function ImpersonationBanner() {
  const { user } = useAuth();
  const isImpersonating =
    !!localStorage.getItem('impersonation_active') ||
    !!localStorage.getItem('admin_access_token');

  if (!isImpersonating) return null;

  const stop = () => {
    const access  = localStorage.getItem('admin_access_token');
    const refresh = localStorage.getItem('admin_refresh_token');
    if (access && refresh) {
      // Admin also had a React session in this browser — restore it.
      localStorage.setItem('access_token',  access);
      localStorage.setItem('refresh_token', refresh);
    } else {
      // Admin came straight from the Django admin (session auth) — just drop
      // the impersonated tokens; their admin session cookie is still valid.
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    localStorage.removeItem('admin_access_token');
    localStorage.removeItem('admin_refresh_token');
    localStorage.removeItem('impersonation_active');
    window.location.href = '/admin/users/user/';
  };

  return (
    <div style={{ background: '#e01e8c' }} className="px-4 py-2 flex items-center justify-between gap-4">
      <p className="text-xs font-semibold text-white">
        Impersonating <span className="underline">{user?.full_name}</span>
        {user?.role && <span className="ml-1.5 opacity-70 capitalize">({user.role})</span>}
        &nbsp;&mdash; changes you make will affect this user&apos;s real account.
      </p>
      <button
        onClick={stop}
        className="flex-shrink-0 text-xs font-bold bg-white/20 hover:bg-white/30 text-white px-3 py-1.5 rounded-lg transition-colors border border-white/30"
      >
        Stop impersonating
      </button>
    </div>
  );
}

function PushPromptBanner() {
  const { permission, isSubscribed, isSupported, subscribe } = usePushNotifications();
  const [dismissed, setDismissed] = useState(() => localStorage.getItem('push_dismissed') === '1');

  if (!isSupported || dismissed || isSubscribed || permission === 'granted' || permission === 'denied') return null;

  return (
    <div className="bg-purple-50 border-b border-purple-200 px-4 py-2.5 flex items-center justify-between gap-4">
      <p className="text-sm text-navy-500">
        <span className="font-semibold">Stay in the loop</span> — enable browser notifications for session updates and messages.
      </p>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={subscribe}
          className="text-xs font-semibold bg-gradient-brand text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity"
        >
          Enable
        </button>
        <button
          onClick={() => { localStorage.setItem('push_dismissed', '1'); setDismissed(true); }}
          className="text-xs text-navy-500/50 hover:text-navy-500 transition-colors"
        >
          Not now
        </button>
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Register service worker
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
  }, []);

  const handleLogout = () => { logout(); navigate('/login'); };
  const visibleNav = navItems.filter(i => {
    if (!user || !i.roles.some(r => userHasRole(user, r as any))) return false;
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden" style={{ background: '#f8f7fc' }}>
      {/* ── Top announcement bar ── */}
      <div className="bg-gradient-brand text-white text-xs py-1.5 text-center font-medium tracking-wide">
        Helping young people become future engineers
      </div>

      {/* ── Admin impersonation banner ── */}
      <ImpersonationBanner />

      {/* ── Push notification permission prompt ── */}
      <PushPromptBanner />

      {/* ── Main header ── */}
      <header className="bg-white border-b border-purple-100 sticky top-0 z-50 shadow-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <Link to={user?.role === 'admin' ? '/admin' : '/'} className="flex items-center space-x-2.5 flex-shrink-0">
              <BrandLogo size={36} />
              <div className="leading-none">
                <p className="text-xs font-semibold text-pink-500 tracking-wide uppercase">
                  Arkwright Engineering Scholars
                </p>
                <p className="text-[11px] text-navy-500/60 font-medium">Mentoring Platform</p>
              </div>
            </Link>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center space-x-0.5">
              {visibleNav.map(item => {
                const active = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                      active
                        ? 'text-pink-500 bg-pink-50 font-semibold'
                        : 'text-navy-500/70 hover:text-navy-500 hover:bg-purple-50'
                    }`}
                  >
                    {item.label}
                    {active && <span className="block h-0.5 bg-pink-500 rounded-full mt-0.5 mx-auto w-4/5" />}
                  </Link>
                );
              })}
            </nav>

            {/* User area */}
            <div className="hidden md:flex items-center space-x-3">
              {user && (
                <>
                  <NotificationBell />
                  <Link to="/profile" className="flex items-center space-x-2 group">
                    <div className="w-8 h-8 rounded-full bg-gradient-brand-soft flex items-center justify-center text-white text-xs font-bold shadow-brand">
                      {user.first_name[0]}{user.last_name[0]}
                    </div>
                    <div className="hidden lg:block leading-none text-right">
                      <p className="text-xs font-semibold text-navy-500 group-hover:text-purple-500 transition-colors">
                        {user.full_name}
                      </p>
                      <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${roleBadgeStyle[user.role] || 'bg-gray-100 text-gray-600'}`}>
                        {user.role}
                      </span>
                    </div>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-xs font-medium text-navy-500/50 hover:text-pink-500 transition-colors"
                  >
                    Sign out
                  </button>
                </>
              )}
            </div>

            {/* Mobile burger */}
            <div className="flex items-center gap-1 md:hidden">
              {user && <NotificationBell />}
              <button
                className="p-2 rounded-lg text-navy-500/60 hover:bg-purple-50"
                onClick={() => setMobileOpen(o => !o)}
                aria-label="Toggle menu"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {mobileOpen
                    ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden border-t border-purple-100 bg-white px-4 py-3 space-y-1">
            {visibleNav.map(item => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                  location.pathname === item.path
                    ? 'text-pink-500 bg-pink-50 font-semibold'
                    : 'text-navy-500/70'
                }`}
              >
                {item.label}
              </Link>
            ))}
            {user && (
              <button
                onClick={handleLogout}
                className="block w-full text-left px-3 py-2 text-sm text-pink-500 font-medium"
              >
                Sign out
              </button>
            )}
          </div>
        )}
      </header>

      {/* ── Page content ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* ── Footer ── */}
      <footer className="bg-gradient-brand text-white mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="flex flex-col sm:flex-row justify-between items-start gap-6">
            <div className="flex items-center space-x-3">
              <BrandLogo size={32} />
              <div>
                <p className="font-bold text-sm">Arkwright Engineering Scholars</p>
                <p className="text-xs text-white/60">Mentoring Platform</p>
              </div>
            </div>
            <div className="text-xs text-white/60 sm:text-right">
              <p>Helping young people become future engineers</p>
              <p className="mt-1">&copy; {new Date().getFullYear()} Smallpeice Trust. All rights reserved.</p>
              <p className="mt-1">All communications on this platform are monitored for safeguarding.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
