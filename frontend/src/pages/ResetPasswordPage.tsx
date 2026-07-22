import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import BrandLogo from '../components/ui/BrandLogo';
import api from '../utils/api';

export default function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/password-reset/confirm/', { uid, token, new_password: password });
      setDone(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: any) {
      setError(err?.response?.data?.error || 'This reset link is invalid or has expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-brand flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/5" />
        <div className="absolute bottom-12 -left-24 w-72 h-72 rounded-full bg-white/5" />
        <div className="absolute top-1/2 left-1/2 w-32 h-32 rounded-full bg-pink-500/20 blur-2xl" />
        <div className="relative z-10">
          <div className="flex items-center space-x-3 mb-12">
            <BrandLogo size={44} />
            <div>
              <p className="font-bold text-white text-sm tracking-wide">Arkwright Engineering Scholars</p>
              <p className="text-white/60 text-xs">Mentoring Platform</p>
            </div>
          </div>
          <h1 className="text-4xl font-extrabold text-white leading-tight">
            Choose a new<br />
            <span className="text-pink-200">password</span>
          </h1>
          <p className="mt-6 text-white/70 text-base leading-relaxed max-w-sm">
            Pick something strong. You'll use it every time you sign in to the mentoring platform.
          </p>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-[#f8f7fc]">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center space-x-2 mb-8">
            <BrandLogo size={32} />
            <p className="font-bold text-navy-500 text-sm">Arkwright Engineering Scholars</p>
          </div>

          {done ? (
            <div>
              <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mb-6">
                <svg className="w-7 h-7 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-extrabold text-navy-500">Password updated!</h2>
              <p className="mt-2 text-sm text-navy-500/60">You're being redirected to sign in…</p>
              <Link to="/login" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-pink-500 hover:text-pink-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
                Sign in now
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-2xl font-extrabold text-navy-500">Set a new password</h2>
              <p className="mt-1 text-sm text-navy-500/50">Choose a strong password for your account.</p>

              <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                <div>
                  <label htmlFor="password" className="block text-xs font-semibold text-navy-500 mb-1.5 uppercase tracking-wider">
                    New password
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full border-2 border-purple-100 rounded-xl px-4 py-3 text-sm text-navy-500 bg-white focus:outline-none focus:border-pink-500 transition-colors"
                  />
                </div>

                <div>
                  <label htmlFor="confirm" className="block text-xs font-semibold text-navy-500 mb-1.5 uppercase tracking-wider">
                    Confirm password
                  </label>
                  <input
                    id="confirm"
                    type="password"
                    value={confirm}
                    onChange={e => setConfirm(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full border-2 border-purple-100 rounded-xl px-4 py-3 text-sm text-navy-500 bg-white focus:outline-none focus:border-pink-500 transition-colors"
                  />
                </div>

                {error && (
                  <div className="bg-pink-50 border border-pink-200 rounded-xl px-4 py-3 text-sm text-pink-700 font-medium flex items-start gap-2">
                    <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-brand-soft text-white py-3 px-6 rounded-xl font-bold text-sm hover:opacity-90 disabled:opacity-60 transition-all shadow-brand flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Saving…
                    </>
                  ) : (
                    <>
                      Set new password
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                    </>
                  )}
                </button>

                <div className="text-center">
                  <Link to="/login" className="text-xs text-navy-500/50 hover:text-pink-500 font-medium transition-colors">
                    Back to sign in
                  </Link>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
