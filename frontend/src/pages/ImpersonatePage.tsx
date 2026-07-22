import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

/**
 * Landing page for admin impersonation.
 * Django admin redirects here with ?access=...&refresh=...&uid=...
 * We stash the current admin tokens, swap in the target user's tokens,
 * fetch their profile, then send them to the dashboard.
 */
export default function ImpersonatePage() {
  const { fetchCurrentUser } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const access  = params.get('access');
    const refresh = params.get('refresh');

    if (!access || !refresh) {
      navigate('/login', { replace: true });
      return;
    }

    // Preserve admin session so we can restore it later. The admin usually
    // arrives via Django-admin session auth with NO React tokens, so also set
    // an explicit marker — the banner must show either way.
    const adminAccess  = localStorage.getItem('access_token');
    const adminRefresh = localStorage.getItem('refresh_token');
    if (adminAccess)  localStorage.setItem('admin_access_token',  adminAccess);
    if (adminRefresh) localStorage.setItem('admin_refresh_token', adminRefresh);
    localStorage.setItem('impersonation_active', '1');

    // Activate the impersonated user's tokens
    localStorage.setItem('access_token',  access);
    localStorage.setItem('refresh_token', refresh);

    fetchCurrentUser().then(() => navigate('/', { replace: true }));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: '#f8f7fc' }}>
      <div className="flex items-center gap-3 text-navy-500/60">
        <div className="w-5 h-5 border-2 border-purple-300 border-t-pink-500 rounded-full animate-spin" />
        <span className="text-sm font-medium">Switching user…</span>
      </div>
    </div>
  );
}
