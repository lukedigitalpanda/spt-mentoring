import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { Forum, Thread, Post, PaginatedResponse } from '../types';

function BrandStar({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <path d="M10 0 L10 20 M0 10 L20 10 M2.93 2.93 L17.07 17.07 M17.07 2.93 L2.93 17.07"
        stroke="#e01e8c" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

const visibilityBadge: Record<string, string> = {
  open:       'bg-green-100 text-green-700',
  programme:  'bg-purple-100 text-purple-700',
  private:    'bg-gray-100 text-gray-600',
};

const statusBadge: Record<string, string> = {
  visible:  'bg-green-100 text-green-700',
  pending:  'bg-yellow-100 text-yellow-700',
  flagged:  'bg-red-100 text-red-700',
  hidden:   'bg-gray-100 text-gray-500',
};

function fmt(d?: string | null) {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ── Forum list ────────────────────────────────────────────────────────────────
function ForumList({ onSelect }: { onSelect: (f: Forum) => void }) {
  const { data, isLoading } = useQuery<PaginatedResponse<Forum>>({
    queryKey: ['forums'],
    queryFn: () => api.get('/forums/').then(r => r.data),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data?.results?.length)
    return <EmptyState message="No forums available yet." />;

  return (
    <div className="space-y-3">
      {data.results.map(forum => (
        <button
          key={forum.id}
          onClick={() => onSelect(forum)}
          className="w-full text-left bg-white rounded-2xl shadow-card hover:shadow-brand transition-all p-5 group"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize ${visibilityBadge[forum.visibility]}`}>
                  {forum.visibility}
                </span>
              </div>
              <h3 className="font-bold text-navy-DEFAULT group-hover:text-pink-DEFAULT transition-colors text-sm">
                {forum.title}
              </h3>
              {forum.description && (
                <p className="text-xs text-navy-DEFAULT/50 mt-1 line-clamp-2">{forum.description}</p>
              )}
            </div>
            <div className="flex flex-col items-end flex-shrink-0 gap-1">
              <span className="text-xs font-bold text-navy-DEFAULT">{forum.thread_count}</span>
              <span className="text-[10px] text-navy-DEFAULT/40">threads</span>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}

// ── Thread list ───────────────────────────────────────────────────────────────
function ThreadList({
  forum,
  onSelect,
  onBack,
}: {
  forum: Forum;
  onSelect: (t: Thread) => void;
  onBack: () => void;
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [firstPost, setFirstPost] = useState('');

  const { data, isLoading } = useQuery<PaginatedResponse<Thread>>({
    queryKey: ['threads', forum.id],
    queryFn: () => api.get(`/forums/threads/?forum=${forum.id}`).then(r => r.data),
  });

  const createThread = useMutation({
    mutationFn: (payload: { forum: number; title: string; first_post: string }) =>
      api.post('/forums/threads/', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', forum.id] });
      setShowForm(false);
      setTitle('');
      setFirstPost('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !firstPost.trim()) return;
    createThread.mutate({ forum: forum.id, title: title.trim(), first_post: firstPost.trim() });
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onBack} className="text-xs font-semibold text-pink-DEFAULT hover:underline flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          Forums
        </button>
        <span className="text-navy-DEFAULT/30">/</span>
        <span className="text-sm font-bold text-navy-DEFAULT truncate">{forum.title}</span>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BrandStar />
          <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">Threads</h2>
        </div>
        {user && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="text-xs font-semibold bg-pink-DEFAULT text-white px-3 py-1.5 rounded-lg hover:bg-pink-600 transition-colors"
          >
            + New thread
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-card p-5 mb-5 space-y-3">
          <h3 className="text-sm font-bold text-navy-DEFAULT">Start a new thread</h3>
          <input
            className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30"
            placeholder="Thread title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            required
          />
          <textarea
            className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 resize-none"
            rows={3}
            placeholder="Write your first message…"
            value={firstPost}
            onChange={e => setFirstPost(e.target.value)}
            required
          />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)} className="text-xs text-navy-DEFAULT/50 px-3 py-1.5 rounded-lg hover:bg-gray-50">
              Cancel
            </button>
            <button
              type="submit"
              disabled={createThread.isPending}
              className="text-xs font-semibold bg-pink-DEFAULT text-white px-4 py-1.5 rounded-lg hover:bg-pink-600 transition-colors disabled:opacity-50"
            >
              {createThread.isPending ? 'Posting…' : 'Post thread'}
            </button>
          </div>
        </form>
      )}

      {isLoading ? <LoadingSpinner /> : !data?.results?.length ? (
        <EmptyState message="No threads yet. Be the first to start a discussion!" />
      ) : (
        <div className="space-y-2">
          {data.results.map(thread => (
            <button
              key={thread.id}
              onClick={() => onSelect(thread)}
              className="w-full text-left bg-white rounded-2xl shadow-card hover:shadow-brand transition-all p-4 group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    {thread.is_pinned && (
                      <span className="text-[10px] font-semibold bg-pink-50 text-pink-DEFAULT px-1.5 py-0.5 rounded-full">Pinned</span>
                    )}
                    {thread.is_locked && (
                      <span className="text-[10px] font-semibold bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">Locked</span>
                    )}
                  </div>
                  <h3 className="font-semibold text-sm text-navy-DEFAULT group-hover:text-pink-DEFAULT transition-colors">
                    {thread.title}
                  </h3>
                  <p className="text-xs text-navy-DEFAULT/40 mt-0.5">
                    Started by {thread.created_by_name} · {fmt(thread.created_at)}
                  </p>
                </div>
                <div className="flex flex-col items-end flex-shrink-0 gap-0.5">
                  <span className="text-xs font-bold text-navy-DEFAULT">{thread.post_count}</span>
                  <span className="text-[10px] text-navy-DEFAULT/40">replies</span>
                  {thread.last_post_at && (
                    <span className="text-[10px] text-navy-DEFAULT/30 mt-1">{fmt(thread.last_post_at)}</span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Post list ─────────────────────────────────────────────────────────────────
function PostList({
  forum,
  thread,
  onBack,
}: {
  forum: Forum;
  thread: Thread;
  onBack: () => void;
}) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [body, setBody] = useState('');

  const { data, isLoading } = useQuery<PaginatedResponse<Post>>({
    queryKey: ['posts', thread.id],
    queryFn: () => api.get(`/forums/posts/?thread=${thread.id}`).then(r => r.data),
  });

  const createPost = useMutation({
    mutationFn: (payload: { thread: number; body: string }) =>
      api.post('/forums/posts/', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts', thread.id] });
      setBody('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;
    createPost.mutate({ thread: thread.id, body: body.trim() });
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <button onClick={() => onBack()} className="text-xs font-semibold text-pink-DEFAULT hover:underline flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          {forum.title}
        </button>
        <span className="text-navy-DEFAULT/30">/</span>
        <span className="text-sm font-bold text-navy-DEFAULT truncate">{thread.title}</span>
      </div>

      {thread.is_locked && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-xs text-gray-500 font-medium mb-4">
          This thread is locked. No new replies can be posted.
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : (
        <div className="space-y-3 mb-6">
          {!data?.results?.length ? (
            <EmptyState message="No posts yet." />
          ) : (
            data.results.map(post => (
              <div key={post.id} className="bg-white rounded-2xl shadow-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-brand-soft flex items-center justify-center text-white text-xs font-bold shadow-brand">
                      {post.author_name?.[0] ?? '?'}
                    </div>
                    <span className="text-xs font-semibold text-navy-DEFAULT">{post.author_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${statusBadge[post.status] ?? ''}`}>
                      {post.status}
                    </span>
                    <span className="text-xs text-navy-DEFAULT/30">{fmt(post.created_at)}</span>
                  </div>
                </div>
                <p className="text-sm text-navy-DEFAULT/80 whitespace-pre-wrap">{post.body}</p>
              </div>
            ))
          )}
        </div>
      )}

      {user && !thread.is_locked && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-card p-5 space-y-3">
          <h3 className="text-sm font-bold text-navy-DEFAULT">Post a reply</h3>
          <textarea
            className="w-full border border-purple-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-DEFAULT/30 resize-none"
            rows={3}
            placeholder="Write your reply…"
            value={body}
            onChange={e => setBody(e.target.value)}
            required
          />
          {createPost.isError && (
            <p className="text-xs text-red-500">Failed to post. Please try again.</p>
          )}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={createPost.isPending || !body.trim()}
              className="text-xs font-semibold bg-pink-DEFAULT text-white px-4 py-1.5 rounded-lg hover:bg-pink-600 transition-colors disabled:opacity-50"
            >
              {createPost.isPending ? 'Posting…' : 'Post reply'}
            </button>
          </div>
          <p className="text-[10px] text-navy-DEFAULT/30">
            All posts are reviewed for safeguarding compliance before becoming visible.
          </p>
        </form>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function LoadingSpinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="w-8 h-8 border-2 border-purple-DEFAULT/30 border-t-pink-DEFAULT rounded-full animate-spin" />
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12 text-sm text-navy-DEFAULT/40">{message}</div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function ForumsPage() {
  const [selectedForum, setSelectedForum] = useState<Forum | null>(null);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);

  return (
    <div>
      {/* Page header */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-brand text-white px-8 py-8 mb-8 shadow-brand">
        <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full bg-white/5" />
        <div className="relative z-10">
          <p className="text-xs font-semibold text-white/60 uppercase tracking-widest mb-1">Community</p>
          <h1 className="text-2xl font-extrabold">Forums</h1>
          <p className="mt-1 text-white/60 text-sm">Discussions, peer support and group mentoring.</p>
        </div>
      </div>

      {!selectedForum && (
        <>
          <div className="flex items-center gap-2 mb-4">
            <BrandStar />
            <h2 className="text-sm font-bold text-navy-DEFAULT uppercase tracking-widest">All Forums</h2>
          </div>
          <ForumList onSelect={setSelectedForum} />
        </>
      )}

      {selectedForum && !selectedThread && (
        <ThreadList
          forum={selectedForum}
          onSelect={setSelectedThread}
          onBack={() => setSelectedForum(null)}
        />
      )}

      {selectedForum && selectedThread && (
        <PostList
          forum={selectedForum}
          thread={selectedThread}
          onBack={() => setSelectedThread(null)}
        />
      )}
    </div>
  );
}
