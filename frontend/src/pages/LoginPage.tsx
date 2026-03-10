import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import BrandLogo from '../components/ui/BrandLogo';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch {
      setError('Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* ── Left panel – gradient brand ── */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-brand flex-col justify-between p-12 relative overflow-hidden">
        {/* Decorative circles */}
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/5" />
        <div className="absolute bottom-12 -left-24 w-72 h-72 rounded-full bg-white/5" />
        <div className="absolute top-1/2 left-1/2 w-32 h-32 rounded-full bg-pink-DEFAULT/20 blur-2xl" />

        <div className="relative z-10">
          <div className="flex items-center space-x-3 mb-12">
            <BrandLogo size={44} />
            <div>
              <p className="font-bold text-white text-sm tracking-wide">Arkwright Engineering Scholars</p>
              <p className="text-white/60 text-xs">Mentoring Platform</p>
            </div>
          </div>

          <h1 className="text-4xl font-extrabold text-white leading-tight">
            Helping young people<br />
            <span className="text-pink-200">become future<br />engineers</span>
          </h1>
          <p className="mt-6 text-white/70 text-base leading-relaxed max-w-sm">
            Connect scholars with mentors and sponsors to build careers in engineering and technology.
          </p>
        </div>

        {/* Bottom stats row */}
        <div className="relative z-10 grid grid-cols-3 gap-4">
          {[
            { value: '60+', label: 'Years inspiring engineers' },
            { value: '1,000+', label: 'Scholars supported' },
            { value: '500+', label: 'Mentor volunteers' },
          ].map(s => (
            <div key={s.label} className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <p className="text-xl font-extrabold text-white">{s.value}</p>
              <p className="text-xs text-white/60 mt-0.5 leading-snug">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel – form ── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-[#f8f7fc]">
        <div className="w-full max-w-md">

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center space-x-2 mb-8">
            <BrandLogo size={32} />
            <p className="font-bold text-navy-DEFAULT text-sm">Arkwright Engineering Scholars</p>
          </div>

          <h2 className="text-2xl font-extrabold text-navy-DEFAULT">Sign in to your account</h2>
          <p className="mt-1 text-sm text-navy-DEFAULT/50">Welcome back – your mentoring journey continues here.</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-navy-DEFAULT mb-1.5 uppercase tracking-wider">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
                className="w-full border-2 border-purple-100 rounded-xl px-4 py-3 text-sm text-navy-DEFAULT bg-white focus:outline-none focus:border-pink-DEFAULT transition-colors placeholder:text-navy-DEFAULT/30"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label htmlFor="password" className="block text-xs font-semibold text-navy-DEFAULT uppercase tracking-wider">
                  Password
                </label>
                <a href="#" className="text-xs text-pink-DEFAULT hover:text-pink-600 font-medium">
                  Forgot password?
                </a>
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full border-2 border-purple-100 rounded-xl px-4 py-3 text-sm text-navy-DEFAULT bg-white focus:outline-none focus:border-pink-DEFAULT transition-colors"
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
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </>
              )}
            </button>
          </form>

          <p className="mt-8 text-center text-xs text-navy-DEFAULT/40 leading-relaxed">
            All communications on this platform are moderated for safeguarding purposes.
            <br />If you need access, contact{' '}
            <a href="mailto:mentoring@smallpeice.co.uk" className="text-pink-DEFAULT hover:underline">
              mentoring@smallpeice.co.uk
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
