import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../utils/api';
import type { Resource, ResourceCategory, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
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
  document: 'bg-purple-50 text-purple-500',
  link:     'bg-orange-50 text-orange-500',
  video:    'bg-pink-50 text-pink-500',
};

// ── Folder card ───────────────────────────────────────────────────────────────
function FolderCard({ category, onClick }: { category: ResourceCategory; onClick: () => void }) {
  const total = category.resource_count + category.children_count;
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-2xl shadow-card hover:shadow-brand transition-all p-5 flex items-start gap-4 group"
    >
      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-100 to-pink-100 flex items-center justify-center flex-shrink-0 group-hover:from-pink-100 group-hover:to-purple-100 transition-all">
        <svg className="w-6 h-6 text-pink-500" fill="currentColor" viewBox="0 0 24 24">
          <path d="M20 6H12l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-bold text-sm text-navy-500 group-hover:text-pink-500 transition-colors">{category.name}</h3>
        {category.description && (
          <p className="text-xs text-navy-500/50 mt-0.5 line-clamp-2">{category.description}</p>
        )}
        <div className="flex items-center gap-3 mt-2 text-[10px] text-navy-500/40 font-semibold uppercase tracking-wide">
          {category.resource_count > 0 && (
            <span>{category.resource_count} file{category.resource_count !== 1 ? 's' : ''}</span>
          )}
          {category.children_count > 0 && (
            <span>{category.children_count} subfolder{category.children_count !== 1 ? 's' : ''}</span>
          )}
          {total === 0 && <span>Empty</span>}
        </div>
      </div>
      <svg className="w-4 h-4 text-navy-500/20 group-hover:text-pink-400 transition-colors flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}

// ── Resource card ─────────────────────────────────────────────────────────────
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
          <h3 className="font-bold text-sm text-navy-500 line-clamp-2 leading-snug">{resource.title}</h3>
          <span className="text-[10px] font-semibold uppercase tracking-wide text-navy-500/40 capitalize mt-0.5 inline-block">
            {resource.resource_type}
          </span>
        </div>
      </div>

      {resource.description && (
        <p className="text-xs text-navy-500/50 line-clamp-3 mb-4 flex-1">{resource.description}</p>
      )}

      <div className="flex items-center justify-between mt-auto pt-3 border-t border-purple-50">
        <span className="text-xs text-navy-500/30 flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {resource.download_count}
        </span>
        {(resource.url || resource.file) && (
          <button
            onClick={handleAction}
            className="text-xs font-semibold text-pink-500 hover:text-pink-600 flex items-center gap-1 transition-colors"
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

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ResourcesPage() {
  // folderPath = stack of { id, name } representing the current location
  const [folderPath, setFolderPath] = useState<{ id: number; name: string }[]>([]);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState('');

  const currentFolderId = folderPath.length > 0 ? folderPath[folderPath.length - 1].id : null;
  const isSearching = search.length > 0 || selectedType !== '';

  // Subfolders inside current folder (or root folders when at root)
  const { data: folders } = useQuery<PaginatedResponse<ResourceCategory>>({
    queryKey: ['resource-categories', currentFolderId],
    queryFn: () => {
      const params = currentFolderId
        ? `/resources/categories/?parent=${currentFolderId}`
        : '/resources/categories/?root=true';
      return api.get(params).then(r => r.data);
    },
    enabled: !isSearching,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  // Resources in the current folder (or search results)
  const resourceParams = new URLSearchParams();
  if (isSearching) {
    if (search) resourceParams.set('search', search);
    if (selectedType) resourceParams.set('resource_type', selectedType);
  } else if (currentFolderId !== null) {
    resourceParams.set('category', String(currentFolderId));
  } else {
    // Root view — show uncategorised resources only
    resourceParams.set('no_category', 'true');
  }

  const { data: resources, isLoading: resourcesLoading } = useQuery<PaginatedResponse<Resource>>({
    queryKey: ['resources', currentFolderId, search, selectedType],
    queryFn: () => api.get(`/resources/?${resourceParams.toString()}`).then(r => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const navigateInto = (cat: ResourceCategory) => {
    setFolderPath(prev => {
      if (prev.length > 0 && prev[prev.length - 1].id === cat.id) return prev;
      return [...prev, { id: cat.id, name: cat.name }];
    });
  };

  const navigateTo = (index: number) => {
    // index -1 = root
    setFolderPath(prev => prev.slice(0, index + 1));
  };

  const hasFolders = (folders?.results?.length ?? 0) > 0;
  const hasResources = (resources?.results?.length ?? 0) > 0;
  const isRootView = currentFolderId === null && !isSearching;

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

      {/* Search & type filter */}
      <div className="bg-white rounded-2xl shadow-card p-4 mb-6 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <svg className="w-4 h-4 text-navy-500/30 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            className="w-full pl-9 pr-3 py-2 text-sm border border-purple-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/30"
            placeholder="Search all resources…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="text-sm border border-purple-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500/30 text-navy-500"
          value={selectedType}
          onChange={e => setSelectedType(e.target.value)}
        >
          <option value="">All types</option>
          <option value="document">Documents</option>
          <option value="link">Links</option>
          <option value="video">Videos</option>
        </select>
      </div>

      {/* Search results mode */}
      {isSearching ? (
        <>
          <div className="flex items-center gap-2 mb-4">
            <BrandStar />
            <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">
              {resources ? `${resources.count} result${resources.count !== 1 ? 's' : ''}` : 'Searching…'}
            </h2>
            <button onClick={() => { setSearch(''); setSelectedType(''); }}
              className="ml-auto text-xs text-pink-500 hover:underline">
              Clear search
            </button>
          </div>
          {resourcesLoading ? (
            <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>
          ) : !hasResources ? (
            <p className="text-center py-16 text-sm text-navy-500/40">No resources match your search.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {resources!.results.map(r => <ResourceCard key={r.id} resource={r} />)}
            </div>
          )}
        </>
      ) : (
        <>
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1 mb-6 flex-wrap">
            <button
              onClick={() => navigateTo(-1)}
              className={`text-sm font-semibold transition-colors ${folderPath.length === 0 ? 'text-navy-500' : 'text-pink-500 hover:text-pink-600'}`}
            >
              Resources
            </button>
            {folderPath.map((crumb, i) => (
              <React.Fragment key={crumb.id}>
                <svg className="w-3.5 h-3.5 text-navy-500/30 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                </svg>
                <button
                  onClick={() => navigateTo(i)}
                  className={`text-sm font-semibold transition-colors ${i === folderPath.length - 1 ? 'text-navy-500' : 'text-pink-500 hover:text-pink-600'}`}
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
          </nav>

          {/* Folders */}
          {hasFolders && (
            <>
              <div className="flex items-center gap-2 mb-3">
                <BrandStar />
                <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Folders</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
                {folders!.results.map(cat => (
                  <FolderCard key={cat.id} category={cat} onClick={() => navigateInto(cat)} />
                ))}
              </div>
            </>
          )}

          {/* Resources in this folder */}
          {resourcesLoading ? (
            <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" /></div>
          ) : hasResources ? (
            <>
              <div className="flex items-center gap-2 mb-4">
                <BrandStar />
                <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">
                  {isRootView ? 'Uncategorised' : 'Files'}
                  <span className="ml-2 text-navy-500/40 normal-case font-normal">({resources!.count})</span>
                </h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {resources!.results.map(r => <ResourceCard key={r.id} resource={r} />)}
              </div>
            </>
          ) : !hasFolders ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 rounded-2xl bg-purple-50 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-purple-300" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20 6H12l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" />
                </svg>
              </div>
              <p className="text-sm text-navy-500/40">This folder is empty.</p>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
