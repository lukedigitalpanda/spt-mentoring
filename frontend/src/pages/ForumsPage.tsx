import React, { useState, useRef } from 'react';
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

// The forum post serializer only returns the attachment URL (no separate
// filename field), so recover a readable name from the storage path.
function attachmentFilename(url: string) {
  try {
    const path = new URL(url, window.location.origin).pathname;
    return decodeURIComponent(path.split('/').pop() || 'Attachment');
  } catch {
    return 'Attachment';
  }
}

function PaperclipIcon({ className = 'w-3.5 h-3.5 flex-shrink-0' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
    </svg>
  );
}

function PencilIcon({ className = 'w-3 h-3' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  );
}

// ── Forum list ────────────────────────────────────────────────────────────────
function ForumList({ onSelect }: { onSelect: (f: Forum) => void }) {
  const { data, isLoading } = useQuery<PaginatedResponse<Forum>>({
    queryKey: ['forums', 'list'],
    queryFn: () => api.get('/forums/forums/').then(r => r.data),
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
              <h3 className="font-bold text-navy-500 group-hover:text-pink-500 transition-colors text-sm">
                {forum.title}
              </h3>
              {forum.description && (
                <p className="text-xs text-navy-500/50 mt-1 line-clamp-2">{forum.description}</p>
              )}
            </div>
            <div className="flex flex-col items-end flex-shrink-0 gap-1">
              <span className="text-xs font-bold text-navy-500">{forum.thread_count}</span>
              <span className="text-[10px] text-navy-500/40">threads</span>
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
        <button onClick={onBack} className="text-xs font-semibold text-pink-500 hover:underline flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          Forums
        </button>
        <span className="text-navy-500/30">/</span>
        <span className="text-sm font-bold text-navy-500 truncate">{forum.title}</span>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BrandStar />
          <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">Threads</h2>
        </div>
        {user && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="text-sm font-semibold bg-pink-500 text-white px-4 py-2 rounded-xl hover:bg-pink-600 transition-colors shadow-brand"
          >
            + New thread
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-card p-5 mb-5 space-y-3">
          <h3 className="text-sm font-bold text-navy-500">Start a new thread</h3>
          <input
            className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors"
            placeholder="Thread title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            required
          />
          <textarea
            className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none"
            rows={3}
            placeholder="Write your first message…"
            value={firstPost}
            onChange={e => setFirstPost(e.target.value)}
            required
          />
          <div className="flex gap-2 justify-end pt-1">
            <button type="button" onClick={() => setShowForm(false)} className="text-sm text-navy-500/60 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button
              type="submit"
              disabled={createThread.isPending || !title.trim() || !firstPost.trim()}
              className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
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
                      <span className="text-[10px] font-semibold bg-pink-50 text-pink-500 px-1.5 py-0.5 rounded-full">Pinned</span>
                    )}
                    {thread.is_locked && (
                      <span className="text-[10px] font-semibold bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">Locked</span>
                    )}
                  </div>
                  <h3 className="font-semibold text-sm text-navy-500 group-hover:text-pink-500 transition-colors">
                    {thread.title}
                  </h3>
                  <p className="text-xs text-navy-500/40 mt-0.5">
                    Started by {thread.created_by_name} · {fmt(thread.created_at)}
                  </p>
                </div>
                <div className="flex flex-col items-end flex-shrink-0 gap-0.5">
                  <span className="text-xs font-bold text-navy-500">{thread.post_count}</span>
                  <span className="text-[10px] text-navy-500/40">replies</span>
                  {thread.last_post_at && (
                    <span className="text-[10px] text-navy-500/30 mt-1">{fmt(thread.last_post_at)}</span>
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
  const [attachment, setAttachment] = useState<File | null>(null);
  const attachRef = useRef<HTMLInputElement>(null);
  const [postNotice, setPostNotice] = useState<{ type: 'flagged' | 'blocked'; text: string } | null>(null);
  const [reportingPostId, setReportingPostId] = useState<number | null>(null);
  const [reportingAuthorId, setReportingAuthorId] = useState<number | null>(null);
  const [reportingPostBody, setReportingPostBody] = useState('');
  const [reportedPostId, setReportedPostId] = useState<number | null>(null);
  const [reportDesc, setReportDesc] = useState('');
  // Editing an existing post uses its own body state, separate from the
  // in-progress new-reply draft, so switching into edit mode never clobbers
  // whatever the author was already composing as a fresh reply.
  const [editingPostId, setEditingPostId] = useState<number | null>(null);
  const [editBody, setEditBody] = useState('');

  const reportAbuse = useMutation({
    mutationFn: ({ authorId, desc, postId, postBody }: { authorId: number; desc: string; postId: number; postBody: string }) =>
      api.post('/messaging/abuse-reports/', {
        reported_user: authorId,
        description: desc || `Reported forum post #${postId}`,
        // Snapshot of the post content so admins can see what was reported
        reported_content: postBody,
      }),
    onSuccess: (_, { postId }) => {
      setReportingPostId(null);
      setReportingAuthorId(null);
      setReportDesc('');
      setReportedPostId(postId);
      setTimeout(() => setReportedPostId(null), 4000);
    },
  });

  const { data, isLoading } = useQuery<PaginatedResponse<Post>>({
    queryKey: ['posts', thread.id],
    queryFn: () => api.get(`/forums/posts/?thread=${thread.id}`).then(r => r.data),
  });

  const createPost = useMutation({
    mutationFn: (payload: FormData) =>
      api.post('/forums/posts/', payload, { headers: { 'Content-Type': 'multipart/form-data' } }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['posts', thread.id] });
      setBody('');
      setAttachment(null);
      if (attachRef.current) attachRef.current.value = '';
      // 202 Accepted means the post is held for moderation review — tell the user.
      const moderationStatus = (res?.data as { moderation_status?: string })?.moderation_status;
      if (moderationStatus === 'pending_review') {
        setPostNotice({
          type: 'flagged',
          text: 'Your post has been submitted and is awaiting review before it becomes visible.',
        });
      } else {
        setPostNotice(null);
      }
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { status?: number; data?: { moderation_status?: string; detail?: string; attachment?: string[] } } };
      const httpStatus = axiosError?.response?.status;
      const moderationStatus = axiosError?.response?.data?.moderation_status;
      const attachmentError = axiosError?.response?.data?.attachment?.[0];

      if (httpStatus === 400 && moderationStatus === 'blocked') {
        setPostNotice({
          type: 'blocked',
          text: 'Your post could not be submitted as it contains restricted content.',
        });
      } else if (httpStatus === 400 && attachmentError) {
        // Server-side attachment validation (e.g. disallowed file type) - surface
        // it rather than failing silently.
        setPostNotice({ type: 'blocked', text: attachmentError });
      } else {
        setPostNotice(null);
      }
    },
  });

  // P2-4: author-only post editing, re-screened server-side. 200 returns the
  // full serialised post; 202/400 only return {detail, moderation_status} (no
  // post body), so those outcomes are reflected by refetching the thread -
  // whose queryset already includes the author's own flagged/hidden posts.
  const editPost = useMutation({
    mutationFn: ({ id, body: newBody }: { id: number; body: string }) =>
      api.patch(`/forums/posts/${id}/`, { body: newBody }),
    onSuccess: (res, { id }) => {
      const moderationStatus = (res?.data as { moderation_status?: string })?.moderation_status;
      if (moderationStatus === 'pending_review') {
        setPostNotice({
          type: 'flagged',
          text: 'Your edited post has been submitted and is awaiting review before it becomes visible again.',
        });
        queryClient.invalidateQueries({ queryKey: ['posts', thread.id] });
      } else {
        setPostNotice(null);
        queryClient.setQueryData<PaginatedResponse<Post>>(['posts', thread.id], (old) =>
          old ? { ...old, results: old.results.map(p => (p.id === id ? (res.data as Post) : p)) } : old
        );
      }
      setEditingPostId(null);
      setEditBody('');
    },
    onError: (error: unknown) => {
      const axiosError = error as { response?: { status?: number; data?: { moderation_status?: string; detail?: string } } };
      const httpStatus = axiosError?.response?.status;
      const moderationStatus = axiosError?.response?.data?.moderation_status;

      if (httpStatus === 400 && moderationStatus === 'blocked') {
        setPostNotice({
          type: 'blocked',
          text: 'Your edited post could not be saved as it contains restricted content.',
        });
        // Refresh so the bubble reflects the now-hidden status; stay in edit
        // mode (editBody keeps the attempted text) so the author can fix it.
        queryClient.invalidateQueries({ queryKey: ['posts', thread.id] });
      } else if (httpStatus === 400) {
        setPostNotice({
          type: 'blocked',
          text: axiosError.response?.data?.detail ?? 'Your post could not be saved. Please try again.',
        });
      } else {
        setPostNotice(null);
      }
    },
  });

  const startEditingPost = (post: Post) => {
    setEditingPostId(post.id);
    setEditBody(post.body);
    setPostNotice(null);
  };

  const cancelEditingPost = () => {
    setEditingPostId(null);
    setEditBody('');
    setPostNotice(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingPostId !== null) {
      if (!editBody.trim()) return;
      setPostNotice(null);
      editPost.mutate({ id: editingPostId, body: editBody.trim() });
      return;
    }
    if (!body.trim()) return;
    setPostNotice(null);
    const fd = new FormData();
    fd.append('thread', String(thread.id));
    fd.append('body', body.trim());
    if (attachment) fd.append('attachment', attachment);
    createPost.mutate(fd);
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <button onClick={() => onBack()} className="text-xs font-semibold text-pink-500 hover:underline flex items-center gap-1">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          {forum.title}
        </button>
        <span className="text-navy-500/30">/</span>
        <span className="text-sm font-bold text-navy-500 truncate">{thread.title}</span>
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
              <div key={post.id} className="bg-white rounded-2xl shadow-card p-5 group">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-brand-soft flex items-center justify-center text-white text-xs font-bold shadow-brand">
                      {post.author_name?.[0] ?? '?'}
                    </div>
                    <span className="text-xs font-semibold text-navy-500">{post.author_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full capitalize ${statusBadge[post.status] ?? ''}`}>
                      {post.status}
                    </span>
                    <span className="text-xs text-navy-500/30">
                      {fmt(post.created_at)}{post.edited_at && ' (edited)'}
                    </span>
                    {user && post.author === user.id && (
                      <button
                        onClick={() => startEditingPost(post)}
                        title="Edit this post"
                        aria-label="Edit this post"
                        className="flex items-center justify-center w-10 h-10 -m-1.5 text-navy-500/40 hover:text-purple-500 transition-colors rounded-full hover:bg-purple-50"
                      >
                        <PencilIcon className="w-3.5 h-3.5" />
                      </button>
                    )}
                    {user && post.author !== user.id && (
                      reportedPostId === post.id ? (
                        <span className="text-[10px] text-green-600 font-semibold flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                          </svg>
                          Reported
                        </span>
                      ) : (
                        <button
                          onClick={() => { setReportingPostId(post.id); setReportingAuthorId(post.author); setReportingPostBody(post.body); }}
                          title="Report this post"
                          className="flex items-center gap-1 text-[10px] text-red-400 hover:text-red-600 font-semibold transition-all px-1.5 py-0.5 rounded hover:bg-red-50 border border-red-100"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                          </svg>
                          Report Abuse
                        </button>
                      )
                    )}
                  </div>
                </div>
                <p className="text-sm text-navy-500/80 whitespace-pre-wrap break-words">{post.body}</p>
                {post.attachment && (
                  <a
                    href={post.attachment}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 mt-2 underline text-xs font-semibold text-purple-600 break-words"
                  >
                    <PaperclipIcon />
                    {attachmentFilename(post.attachment)}
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {user && (!thread.is_locked || editingPostId !== null) && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-card p-5 space-y-3">
          {editingPostId !== null ? (
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-navy-500 flex items-center gap-1.5">
                <PencilIcon className="w-3.5 h-3.5 text-purple-500" />
                Editing post
              </h3>
              <button
                type="button"
                onClick={cancelEditingPost}
                className="text-xs font-semibold text-navy-500/50 hover:text-navy-500 underline"
              >
                Cancel
              </button>
            </div>
          ) : (
            <h3 className="text-sm font-bold text-navy-500">Post a reply</h3>
          )}
          <textarea
            className="w-full border border-purple-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500/30 focus:border-pink-500 transition-colors resize-none"
            rows={3}
            placeholder={editingPostId !== null ? 'Edit your post…' : 'Write your reply…'}
            value={editingPostId !== null ? editBody : body}
            onChange={e => (editingPostId !== null ? setEditBody(e.target.value) : setBody(e.target.value))}
            required
          />
          {editingPostId === null && (
            <div className="flex items-center gap-2">
              <input
                ref={attachRef}
                type="file"
                className="hidden"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip"
                onChange={e => setAttachment(e.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                onClick={() => attachRef.current?.click()}
                title="Attach a file"
                className="flex-shrink-0 text-navy-500/40 hover:text-purple-500 transition-colors p-1"
              >
                <PaperclipIcon className="w-5 h-5" />
              </button>
              {attachment && (
                <span className="text-xs text-navy-500/60 truncate flex items-center gap-1.5">
                  {attachment.name}
                  <button
                    type="button"
                    onClick={() => { setAttachment(null); if (attachRef.current) attachRef.current.value = ''; }}
                    title="Remove attachment"
                    className="text-navy-500/30 hover:text-red-500 flex-shrink-0"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              )}
            </div>
          )}
          {postNotice && (
            <div className={`px-3 py-2 rounded-lg text-xs font-medium flex items-start gap-2 ${
              postNotice.type === 'blocked'
                ? 'bg-red-50 border border-red-100 text-red-600'
                : 'bg-yellow-50 border border-yellow-100 text-yellow-700'
            }`}>
              <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
              {postNotice.text}
            </div>
          )}
          {createPost.isError && !postNotice && editingPostId === null && (
            <p className="text-xs text-red-500">Failed to post. Please try again.</p>
          )}
          {editPost.isError && !postNotice && editingPostId !== null && (
            <p className="text-xs text-red-500">Failed to save your edit. Please try again.</p>
          )}
          <div className="flex justify-end">
            {editingPostId !== null ? (
              <button
                type="submit"
                disabled={editPost.isPending || !editBody.trim()}
                className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
              >
                {editPost.isPending ? 'Saving…' : 'Save changes'}
              </button>
            ) : (
              <button
                type="submit"
                disabled={createPost.isPending || !body.trim()}
                className="text-sm font-semibold bg-pink-500 text-white px-5 py-2 rounded-lg hover:bg-pink-600 transition-colors disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
              >
                {createPost.isPending ? 'Posting…' : 'Post reply'}
              </button>
            )}
          </div>
          <p className="text-[10px] text-navy-500/30">
            All posts are reviewed for safeguarding compliance before becoming visible.
          </p>
        </form>
      )}

      {/* Report post modal */}
      {reportingPostId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-80 mx-4">
            <h3 className="font-bold text-navy-500 mb-1">Report this post?</h3>
            <p className="text-xs text-navy-500/50 mb-4">This will be reviewed by our safeguarding team immediately.</p>
            <textarea
              className="w-full border border-purple-100 rounded-xl px-3 py-2 text-sm text-navy-500 resize-none focus:outline-none focus:ring-2 focus:ring-pink-500/30 mb-3"
              rows={3}
              placeholder="Briefly describe your concern…"
              value={reportDesc}
              onChange={e => setReportDesc(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                onClick={() => reportAbuse.mutate({ postId: reportingPostId, authorId: reportingAuthorId!, desc: reportDesc, postBody: reportingPostBody })}
                disabled={reportAbuse.isPending}
                className="flex-1 bg-pink-500 text-white text-sm font-semibold py-2 rounded-xl hover:bg-pink-600 disabled:opacity-50 transition-colors"
              >
                {reportAbuse.isPending ? 'Submitting…' : 'Submit Report'}
              </button>
              <button
                onClick={() => { setReportingPostId(null); setReportingAuthorId(null); setReportDesc(''); }}
                className="flex-1 border border-purple-100 text-navy-500/60 text-sm font-medium py-2 rounded-xl hover:bg-purple-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function LoadingSpinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="w-8 h-8 border-2 border-purple-500/30 border-t-pink-500 rounded-full animate-spin" />
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12 text-sm text-navy-500/40">{message}</div>
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
            <h2 className="text-sm font-bold text-navy-500 uppercase tracking-widest">All Forums</h2>
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
