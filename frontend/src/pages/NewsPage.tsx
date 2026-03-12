import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import type { NewsItem, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

const audienceBadge: Record<string, string> = {
  all:     'bg-green-100 text-green-700',
  scholar: 'bg-purple-100 text-purple-700',
  mentor:  'bg-navy-100 text-navy-DEFAULT',
  sponsor: 'bg-orange-100 text-orange-700',
};

function fmt(d?: string | null) {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

function FeaturedCard({ item }: { item: NewsItem }) {
  return (
    <Link to={`/news/${item.id}`} className="group relative rounded-2xl overflow-hidden block mb-6">
      <div className="bg-gradient-brand px-8 py-10 md:px-12 md:py-14">
        {item.cover_image && (
          <img src={item.cover_image} alt="" className="absolute inset-0 w-full h-full object-cover opacity-10" />
        )}
        <div className="relative z-10 max-w-2xl">
          <div className="flex items-center gap-2 mb-3">
            <BrandStar size={14} />
            <span className="text-xs font-semibold text-pink-200 uppercase tracking-wider">Featured</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-white leading-snug group-hover:text-pink-200 transition-colors">
            {item.title}
          </h2>
          {item.summary && (
            <p className="mt-2 text-white/60 text-sm line-clamp-2">{item.summary}</p>
          )}
          <div className="flex items-center gap-4 mt-4">
            <span className="text-xs text-white/40">{fmt(item.published_at)}</span>
            {item.author_name && <span className="text-xs text-white/40">by {item.author_name}</span>}
          </div>
          <span className="mt-5 inline-flex items-center gap-2 bg-pink-DEFAULT text-white text-xs font-bold px-4 py-2 rounded-lg group-hover:bg-pink-600 transition-colors">
            Read article
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}

function NewsCard({ item }: { item: NewsItem }) {
  return (
    <Link
      to={`/news/${item.id}`}
      className="group bg-white rounded-2xl shadow-card hover:shadow-brand transition-all overflow-hidden flex flex-col"
    >
      {item.cover_image ? (
        <img src={item.cover_image} alt={item.title} className="w-full h-40 object-cover" />
      ) : (
        <div className="w-full h-40 bg-gradient-brand-soft opacity-80 flex items-center justify-center">
          <svg className="w-8 h-8 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
          </svg>
        </div>
      )}
      <div className="p-5 flex flex-col flex-1">
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${audienceBadge[item.audience] ?? ''}`}>
            {item.audience}
          </span>
        </div>
        <h3 className="font-bold text-sm text-navy-DEFAULT group-hover:text-pink-DEFAULT transition-colors leading-snug line-clamp-2 flex-1">
          {item.title}
        </h3>
        {item.summary && (
          <p className="text-xs text-navy-DEFAULT/50 mt-2 line-clamp-3">{item.summary}</p>
        )}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-purple-50">
          <span className="text-xs text-navy-DEFAULT/30">{fmt(item.published_at)}</span>
          <span className="text-xs font-semibold text-pink-DEFAULT flex items-center gap-1">
            Read
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function NewsPage() {
  const [audience, setAudience] = useState('');
  const [search, setSearch] = useState('');

  const params = new URLSearchParams({ status: 'published' });
  if (audience) params.set('audience', audience);
  if (search) params.set('search', search);

  const { data, isLoading } = useQuery<PaginatedResponse<NewsItem>>({
    queryKey: ['news', audience, search],
    queryFn: () => api.get(`/news/items/?${params.toString()}`).then(r => r.data),
  });

  const featured = data?.results?.find(n => n.is_featured);
  const rest = data?.results?.filter(n => !n.is_featured) ?? [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <p className="text-xs font-semibold text-navy-DEFAULT/40 uppercase tracking-widest mb-0.5">Latest from the programme</p>
          <h1 className="text-2xl font-extrabold text-navy-DEFAULT">News</h1>
        </div>

        {/* Filters */}
        <div className="flex gap-2 flex-wrap">
          <div className="relative">
            <svg className="w-3.5 h-3.5 text-navy-DEFAULT/30 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              className="pl-8 pr-3 py-1.5 text-sm border border-purple-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 w-44"
              placeholder="Search…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select
            className="text-sm border border-purple-100 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 text-navy-DEFAULT"
            value={audience}
            onChange={e => setAudience(e.target.value)}
          >
            <option value="">All audiences</option>
            <option value="all">General</option>
            <option value="scholar">Scholars</option>
            <option value="mentor">Mentors</option>
            <option value="sponsor">Sponsors</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" />
        </div>
      ) : !data?.results?.length ? (
        <div className="text-center py-16 text-sm text-navy-DEFAULT/40">No articles found.</div>
      ) : (
        <>
          {featured && <FeaturedCard item={featured} />}

          {rest.length > 0 && (
            <>
              <div className="flex items-center gap-2 mb-4">
                <BrandStar />
                <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">All Articles</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {rest.map(item => <NewsCard key={item.id} item={item} />)}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
