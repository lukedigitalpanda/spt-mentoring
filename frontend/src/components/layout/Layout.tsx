import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../hooks/useAuth';
import { usePushNotifications } from '../../hooks/usePushNotifications';
import BrandLogo from '../ui/BrandLogo';
import api from '../../utils/api';

const navItems = [
  { path: '/',           label: 'Home',             roles: ['scholar','mentor','sponsor','alumni','admin'] },
  { path: '/messages',   label: 'Messages',         roles: ['scholar','mentor','sponsor','alumni','admin'] },
  { path: '/sessions',   label: 'Sessions',         roles: ['scholar','mentor','alumni','admin'] },
  { path: '/goals',      label: 'Goals',            roles: ['scholar','mentor','alumni','admin'] },
  { path: '/mentors',    label: 'Find a Mentor',    roles: ['scholar','alumni'] },
  { path: '/forums',     label: 'Forums',           roles: ['scholar','mentor','alumni','admin'] },
  { path: '/resources',  label: 'Resources',        roles: ['scholar','mentor','sponsor','alumni','admin'] },
  { path: '/surveys',    label: 'Surveys',          roles: ['scholar','mentor','admin'] },
  { path: '/news',       label: 'News',             roles: ['scholar','mentor','sponsor','alumni','admin'] },
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
      className="relative p-1.5 text-navy-DEFAULT/50 hover:text-navy-DEFAULT transition-colors">
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-pink-DEFAULT rounded-full text-[9px] font-bold text-white flex items-center justify-center">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  );
}

function PushPromptBanner() {
  const { permission, isSubscribed, isSupported, subscribe } = usePushNotifications();
  const [dismissed, setDismissed] = useState(() => localStorage.getItem('push_dismissed') === '1');

  if (!isSupported || dismissed || isSubscribed || permission === 'granted' || permission === 'denied') return null;

  return (
    <div className="bg-purple-50 border-b border-purple-200 px-4 py-2.5 flex items-center justify-between gap-4">
      <p className="text-sm text-navy-DEFAULT">
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
          className="text-xs text-navy-DEFAULT/50 hover:text-navy-DEFAULT transition-colors"
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
  const visibleNav = navItems.filter(i => user && i.roles.includes(user.role));

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#f8f7fc' }}>
      {/* ── Top announcement bar ── */}
      <div className="bg-gradient-brand text-white text-xs py-1.5 text-center font-medium tracking-wide">
        Helping young people become future engineers
      </div>

      {/* ── Push notification permission prompt ── */}
      <PushPromptBanner />

      {/* ── Main header ── */}
      <header className="bg-white border-b border-purple-100 sticky top-0 z-50 shadow-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2.5 flex-shrink-0">
              <BrandLogo size={36} />
              <div className="leading-none">
                <p className="text-xs font-semibold text-pink-DEFAULT tracking-wide uppercase">
                  Arkwright Engineering Scholars
                </p>
                <p className="text-[11px] text-navy-DEFAULT/60 font-medium">Mentoring Platform</p>
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
                        ? 'text-pink-DEFAULT bg-pink-50 font-semibold'
                        : 'text-navy-DEFAULT/70 hover:text-navy-DEFAULT hover:bg-purple-50'
                    }`}
                  >
                    {item.label}
                    {active && <span className="block h-0.5 bg-pink-DEFAULT rounded-full mt-0.5 mx-auto w-4/5" />}
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
                      <p className="text-xs font-semibold text-navy-DEFAULT group-hover:text-purple-DEFAULT transition-colors">
                        {user.full_name}
                      </p>
                      <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${roleBadgeStyle[user.role] || 'bg-gray-100 text-gray-600'}`}>
                        {user.role}
                      </span>
                    </div>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-xs font-medium text-navy-DEFAULT/50 hover:text-pink-DEFAULT transition-colors"
                  >
                    Sign out
                  </button>
                </>
              )}
            </div>

            {/* Mobile burger */}
            <button
              className="md:hidden p-2 rounded-lg text-navy-DEFAULT/60 hover:bg-purple-50"
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
                    ? 'text-pink-DEFAULT bg-pink-50 font-semibold'
                    : 'text-navy-DEFAULT/70'
                }`}
              >
                {item.label}
              </Link>
            ))}
            {user && (
              <button
                onClick={handleLogout}
                className="block w-full text-left px-3 py-2 text-sm text-pink-DEFAULT font-medium"
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
