import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const navItems = [
  { path: '/', label: 'Home', roles: ['scholar', 'mentor', 'sponsor', 'alumni', 'admin'] },
  { path: '/messages', label: 'Messages', roles: ['scholar', 'mentor', 'sponsor', 'alumni', 'admin'] },
  { path: '/forums', label: 'Forums', roles: ['scholar', 'mentor', 'alumni', 'admin'] },
  { path: '/resources', label: 'Resources', roles: ['scholar', 'mentor', 'sponsor', 'alumni', 'admin'] },
  { path: '/surveys', label: 'Surveys', roles: ['scholar', 'mentor', 'admin'] },
  { path: '/news', label: 'News', roles: ['scholar', 'mentor', 'sponsor', 'alumni', 'admin'] },
  { path: '/admin', label: 'Admin', roles: ['admin'] },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const visibleNav = navItems.filter(
    (item) => user && item.roles.includes(user.role)
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <Link to="/" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-700 rounded flex items-center justify-center">
                  <span className="text-white font-bold text-sm">SPT</span>
                </div>
                <span className="font-semibold text-gray-900">Mentoring Platform</span>
              </Link>
              <nav className="hidden md:flex space-x-1">
                {visibleNav.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      location.pathname === item.path
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              {user && (
                <>
                  <span className="text-sm text-gray-600">
                    {user.full_name}{' '}
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full capitalize">
                      {user.role}
                    </span>
                  </span>
                  <Link to="/profile" className="text-sm text-gray-600 hover:text-gray-900">
                    Profile
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-sm text-red-600 hover:text-red-700"
                  >
                    Sign out
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-gray-500">
          &copy; {new Date().getFullYear()} SPT Mentoring Platform. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
