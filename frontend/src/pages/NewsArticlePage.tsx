import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../utils/api';
import type { NewsItem } from '../types';

function fmt(d?: string | null) {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

export default function NewsArticlePage() {
  const { id } = useParams<{ id: string }>();

  const { data: item, isLoading, isError } = useQuery<NewsItem>({
    queryKey: ['news-article', id],
    queryFn: () => api.get(`/news/items/${id}/`).then(r => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" />
      </div>
    );
  }

  if (isError || !item) {
    return (
      <div className="text-center py-16">
        <p className="text-sm text-navy-DEFAULT/50 mb-4">Article not found.</p>
        <Link to="/news" className="text-xs font-semibold text-pink-DEFAULT hover:underline">
          ← Back to News
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back */}
      <Link
        to="/news"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-pink-DEFAULT hover:underline mb-6"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
        </svg>
        Back to News
      </Link>

      {/* Cover image */}
      {item.cover_image && (
        <img
          src={item.cover_image}
          alt={item.title}
          className="w-full h-64 md:h-80 object-cover rounded-2xl mb-8 shadow-card"
        />
      )}

      {/* Meta */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {item.is_featured && (
            <span className="text-xs font-semibold bg-pink-50 text-pink-DEFAULT px-2.5 py-1 rounded-full">
              Featured
            </span>
          )}
          <span className="text-xs font-semibold bg-purple-50 text-purple-DEFAULT px-2.5 py-1 rounded-full capitalize">
            {item.audience === 'all' ? 'General' : item.audience}
          </span>
        </div>

        <h1 className="text-3xl font-extrabold text-navy-DEFAULT leading-snug">{item.title}</h1>

        <div className="flex items-center gap-3 mt-3 text-xs text-navy-DEFAULT/40">
          {item.author_name && <span>By {item.author_name}</span>}
          {item.published_at && (
            <>
              <span>·</span>
              <span>{fmt(item.published_at)}</span>
            </>
          )}
        </div>
      </div>

      {/* Summary */}
      {item.summary && (
        <p className="text-base text-navy-DEFAULT/70 font-medium leading-relaxed border-l-4 border-pink-DEFAULT pl-4 mb-8">
          {item.summary}
        </p>
      )}

      {/* Body */}
      {item.body && (
        <div className="prose prose-sm max-w-none text-navy-DEFAULT/80 leading-relaxed whitespace-pre-wrap">
          {item.body}
        </div>
      )}

      {/* Footer */}
      <div className="mt-12 pt-6 border-t border-purple-50 flex justify-between items-center">
        <Link to="/news" className="text-xs font-semibold text-pink-DEFAULT hover:underline flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          Back to News
        </Link>
      </div>
    </div>
  );
}
