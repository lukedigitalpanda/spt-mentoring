import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../utils/api';
import type { Resource, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

interface ResourceCategory {
  id: number;
  name: string;
  description: string;
}

const typeIcon: Record<string, React.ReactNode> = {
  document: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  link: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  ),
  video: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.723v6.554a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
};

const typeColour: Record<string, string> = {
  document: 'bg-purple-50 text-purple-DEFAULT',
  link:     'bg-orange-50 text-orange-DEFAULT',
  video:    'bg-pink-50 text-pink-DEFAULT',
};

const audienceBadge: Record<string, string> = {
  all:     'bg-green-100 text-green-700',
  scholar: 'bg-purple-100 text-purple-700',
  mentor:  'bg-navy-100 text-navy-DEFAULT',
  sponsor: 'bg-orange-100 text-orange-700',
  admin:   'bg-gray-100 text-gray-600',
};

function ResourceCard({ resource }: { resource: Resource }) {
  const downloadMutation = useMutation({
    mutationFn: () => api.post(`/resources/${resource.id}/download/`),
  });

  const handleAction = () => {
    downloadMutation.mutate();
    if (resource.resource_type === 'link' && resource.url) {
      window.open(resource.url, '_blank', 'noopener,noreferrer');
    } else if (resource.file) {
      window.open(resource.file, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-card hover:shadow-brand transition-all p-5 flex flex-col">
      <div className="flex items-start gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${typeColour[resource.resource_type] ?? 'bg-gray-100 text-gray-500'}`}>
          {typeIcon[resource.resource_type]}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-sm text-navy-DEFAULT line-clamp-2 leading-snug">{resource.title}</h3>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-navy-DEFAULT/40 capitalize">
              {resource.resource_type}
            </span>
            <span className="text-navy-DEFAULT/20">·</span>
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${audienceBadge[resource.audience] ?? ''}`}>
              {resource.audience}
            </span>
          </div>
        </div>
      </div>

      {resource.description && (
        <p className="text-xs text-navy-DEFAULT/50 line-clamp-3 mb-4 flex-1">{resource.description}</p>
      )}

      <div className="flex items-center justify-between mt-auto pt-3 border-t border-purple-50">
        <span className="text-xs text-navy-DEFAULT/30 flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {resource.download_count}
        </span>
        {(resource.url || resource.file) && (
          <button
            onClick={handleAction}
            className="text-xs font-semibold text-pink-DEFAULT hover:text-pink-600 flex items-center gap-1 transition-colors"
          >
            {resource.resource_type === 'link' ? 'Open link' : 'Download'}
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

export default function ResourcesPage() {
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [selectedType, setSelectedType] = useState<string>('');
  const [search, setSearch] = useState('');

  const { data: categories } = useQuery<PaginatedResponse<ResourceCategory>>({
    queryKey: ['resource-categories'],
    queryFn: () => api.get('/resources/categories/').then(r => r.data),
  });

  const params = new URLSearchParams();
  if (selectedCategory) params.set('category', String(selectedCategory));
  if (selectedType) params.set('resource_type', selectedType);
  if (search) params.set('search', search);

  const { data: resources, isLoading } = useQuery<PaginatedResponse<Resource>>({
    queryKey: ['resources', selectedCategory, selectedType, search],
    queryFn: () => api.get(`/resources/?${params.toString()}`).then(r => r.data),
  });

  return (
    <div>
      {/* Header */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-8 mb-8 shadow-brand">
        <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full bg-white/5" />
        <div className="relative z-10">
          <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1">Library</p>
          <h1 className="text-2xl font-extrabold">Resources</h1>
          <p className="mt-1 text-white/60 text-sm">Documents, guides and links to support your journey.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-card p-4 mb-6 flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <svg className="w-4 h-4 text-navy-DEFAULT/30 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            className="w-full pl-9 pr-3 py-2 text-sm border border-purple-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30"
            placeholder="Search resources…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Type filter */}
        <select
          className="text-sm border border-purple-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 text-navy-DEFAULT"
          value={selectedType}
          onChange={e => setSelectedType(e.target.value)}
        >
          <option value="">All types</option>
          <option value="document">Documents</option>
          <option value="link">Links</option>
          <option value="video">Videos</option>
        </select>

        {/* Category filter */}
        {categories?.results && categories.results.length > 0 && (
          <select
            className="text-sm border border-purple-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 text-navy-DEFAULT"
            value={selectedCategory ?? ''}
            onChange={e => setSelectedCategory(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">All categories</option>
            {categories.results.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Category pills */}
      {categories?.results && categories.results.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`text-xs font-semibold px-3 py-1.5 rounded-full transition-all ${
              selectedCategory === null
                ? 'bg-pink-DEFAULT text-white shadow-brand'
                : 'bg-white text-navy-DEFAULT/60 shadow-card hover:shadow-brand'
            }`}
          >
            All
          </button>
          {categories.results.map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id === selectedCategory ? null : cat.id)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-full transition-all ${
                selectedCategory === cat.id
                  ? 'bg-pink-DEFAULT text-white shadow-brand'
                  : 'bg-white text-navy-DEFAULT/60 shadow-card hover:shadow-brand'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}

      {/* Results */}
      <div className="flex items-center gap-2 mb-4">
        <BrandStar />
        <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">
          {resources ? `${resources.count} resource${resources.count !== 1 ? 's' : ''}` : 'Resources'}
        </h2>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" />
        </div>
      ) : !resources?.results?.length ? (
        <div className="text-center py-16">
          <p className="text-sm text-navy-DEFAULT/40">No resources found matching your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {resources.results.map(r => (
            <ResourceCard key={r.id} resource={r} />
          ))}
        </div>
      )}
    </div>
  );
}
