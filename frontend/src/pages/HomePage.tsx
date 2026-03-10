import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { NewsItem, PaginatedResponse } from '../types';

function FeaturedNewsBanner({ item }: { item: NewsItem }) {
  return (
    <div className="relative rounded-xl overflow-hidden bg-blue-700 text-white p-8 mb-8">
      {item.cover_image && (
        <img
          src={item.cover_image}
          alt={item.title}
          className="absolute inset-0 w-full h-full object-cover opacity-20"
        />
      )}
      <div className="relative">
        <span className="text-xs font-medium bg-white/20 px-2 py-1 rounded">Featured</span>
        <h2 className="mt-3 text-2xl font-bold">{item.title}</h2>
        <p className="mt-2 text-blue-100 max-w-2xl">{item.summary}</p>
        <Link to={`/news/${item.id}`} className="mt-4 inline-block bg-white text-blue-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-50">
          Read more
        </Link>
      </div>
    </div>
  );
}

function QuickStatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

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

  return (
    <div>
      {/* Welcome banner */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.first_name}
        </h1>
        <p className="mt-1 text-gray-500 capitalize">{user?.role} &bull; SPT Mentoring Platform</p>
      </div>

      {/* Featured news */}
      {featured && <FeaturedNewsBanner item={featured} />}

      {/* Quick stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <QuickStatCard label="Last message sent" value={activity?.last_message_sent ? new Date(activity.last_message_sent).toLocaleDateString('en-GB') : 'Never'} />
        <QuickStatCard label="Last message received" value={activity?.last_message_received ? new Date(activity.last_message_received).toLocaleDateString('en-GB') : 'Never'} />
        <QuickStatCard label="Unread messages" value="—" sub="Check Messages" />
        <QuickStatCard label="New resources" value="—" sub="Check Resources" />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Link to="/messages" className="bg-white rounded-lg border border-gray-200 p-6 hover:border-blue-300 hover:shadow-md transition-all text-center group">
          <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:bg-blue-100">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h3 className="font-medium text-gray-900">Messages</h3>
          <p className="text-sm text-gray-500 mt-1">Send and receive messages</p>
        </Link>
        <Link to="/forums" className="bg-white rounded-lg border border-gray-200 p-6 hover:border-blue-300 hover:shadow-md transition-all text-center group">
          <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:bg-green-100">
            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
            </svg>
          </div>
          <h3 className="font-medium text-gray-900">Forums</h3>
          <p className="text-sm text-gray-500 mt-1">Community discussions</p>
        </Link>
        <Link to="/resources" className="bg-white rounded-lg border border-gray-200 p-6 hover:border-blue-300 hover:shadow-md transition-all text-center group">
          <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:bg-purple-100">
            <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="font-medium text-gray-900">Resources</h3>
          <p className="text-sm text-gray-500 mt-1">Documents, links &amp; guides</p>
        </Link>
      </div>

      {/* Recent news list */}
      {news && news.results.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Latest News</h2>
          <div className="space-y-3">
            {news.results.slice(0, 5).map((item) => (
              <Link key={item.id} to={`/news/${item.id}`} className="block bg-white rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition-colors">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium text-gray-900">{item.title}</h3>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{item.summary}</p>
                  </div>
                  <span className="text-xs text-gray-400 ml-4 whitespace-nowrap">
                    {item.published_at ? new Date(item.published_at).toLocaleDateString('en-GB') : ''}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
