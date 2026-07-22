import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import { userHasRole } from '../utils/roles';
import RichText from '../components/ui/RichText';
import type { Conversation, Message } from '../types';

// Touch-first devices get Enter-inserts-newline; sending is via the button only.
const IS_COARSE_POINTER =
  typeof window !== 'undefined' && (window.matchMedia?.('(pointer: coarse)').matches ?? false);

// Per-conversation draft persistence key - survives an orientation-change reload
// in the same tab (sessionStorage), unlike component state.
const draftKey = (id: number) => `chat-draft-${id}`;

// The backend sends a bare, category-level reason fragment (e.g. "it contains
// a web link") - never the sender's actual matched text. The frontend must
// compose this into a full sentence; the bare fragment must never be shown
// on its own. Fall back to generic copy when `reason` is missing (older
// payloads, or WS/REST paths that do not carry one).
const composeFlaggedText = (reason?: string) =>
  reason
    ? `Your message has been held for review because ${reason}. A moderator will check it shortly.`
    : 'Your message has been submitted and is awaiting review before delivery.';

const composeBlockedText = (reason?: string, fallbackDetail?: string) =>
  reason
    ? `Your message could not be sent because ${reason}. Please edit it and try again.`
    : fallbackDetail || 'Your message could not be sent. Please try again.';

// P3-1: day separators in the message list - "Today"/"Yesterday" for the
// last two calendar days, otherwise a full weekday/date label.
const dayLabel = (iso: string) => {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
};

// P2-4: own messages stay editable while flagged/blocked (any time - the
// sender needs to be able to fix and resubmit), and for a short window after
// clean delivery. Attachment messages (body is just the filename) and
// broadcast/mass-message conversations are never editable.
const MESSAGE_EDIT_WINDOW_MS = 15 * 60 * 1000;

function isMessageEditable(msg: Message, isMine: boolean, conversationType?: string): boolean {
  if (!isMine || msg.attachment) return false;
  if (conversationType === 'mass_message') return false;
  if (msg.status === 'flagged' || msg.status === 'blocked') return true;
  if (msg.status === 'delivered') {
    return Date.now() - new Date(msg.sent_at).getTime() <= MESSAGE_EDIT_WINDOW_MS;
  }
  return false;
}

function PencilIcon({ className = 'w-3.5 h-3.5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  );
}

function ReportForm({ onSubmit, onCancel, isPending }: {
  onSubmit: (description: string) => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  const [desc, setDesc] = React.useState('');
  return (
    <>
      <textarea
        className="w-full border border-purple-100 rounded-xl px-3 py-2 text-sm text-navy-500 resize-none focus:outline-none focus:ring-2 focus:ring-pink-500/30 mb-3"
        rows={3}
        placeholder="Briefly describe your concern…"
        value={desc}
        onChange={e => setDesc(e.target.value)}
      />
      <div className="flex gap-2">
        <button
          onClick={() => onSubmit(desc || 'Reported by user')}
          disabled={isPending}
          className="flex-1 bg-pink-500 text-white text-sm font-semibold py-2 rounded-xl hover:bg-pink-600 disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Submitting…' : 'Submit Report'}
        </button>
        <button
          onClick={onCancel}
          className="flex-1 border border-purple-100 text-navy-500/60 text-sm font-medium py-2 rounded-xl hover:bg-purple-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </>
  );
}

export default function MessagesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [selectedConv, setSelectedConv] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [reportingMsgId, setReportingMsgId] = useState<number | null>(null);
  const [reportingMsgSender, setReportingMsgSender] = useState<number | null>(null);
  // Locally-reported message ids this session, merged with the persisted set
  // fetched from the server so the "Reported" state never silently reverts.
  const [locallyReported, setLocallyReported] = useState<Set<number>>(new Set());
  const [moderationNotice, setModerationNotice] = useState<{ type: 'flagged' | 'blocked'; text: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [wsMessages, setWsMessages] = useState<Message[]>([]);
  const attachRef = useRef<HTMLInputElement>(null);
  const [attachPending, setAttachPending] = useState(false);
  // Editing an existing message uses a separate composer state so the
  // in-progress new-message draft (and its sessionStorage persistence) is
  // never touched while editing - cancelling simply drops back to it untouched.
  const [editingMsgId, setEditingMsgId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState('');
  // In-flight guard for saveEditedMessage - mirrors the forum edit mutation's
  // isPending gate, so a slow PATCH can't be double-submitted via Enter/Save.
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const autoGrow = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'; // ~6 lines, then internal scroll
  };

  const contactSupport = useMutation({
    mutationFn: () => api.post('/messaging/conversations/contact_support/').then(r => r.data as Conversation),
    onSuccess: (conv) => {
      qc.invalidateQueries({ queryKey: ['conversations'] });
      setSelectedConv(conv.id);
    },
  });

  const [sponsorError, setSponsorError] = useState<string | null>(null);
  const contactSponsor = useMutation({
    mutationFn: (scholarId?: number) =>
      api.post('/messaging/conversations/contact_sponsor/', scholarId ? { scholar_id: scholarId } : {}).then(r => r.data as Conversation),
    onSuccess: (conv) => {
      setSponsorError(null);
      qc.invalidateQueries({ queryKey: ['conversations'] });
      setSelectedConv(conv.id);
    },
    onError: (err: any) => {
      setSponsorError(err?.response?.data?.error ?? 'Could not open sponsor conversation. Please try again.');
    },
  });

  const { data: conversations } = useQuery<{ results: Conversation[] }>({
    queryKey: ['conversations'],
    // The API is paginated (25/page) — follow every page so long-standing users
    // (e.g. recipients of many mass messages) never lose conversations from the sidebar.
    queryFn: async () => {
      const all: Conversation[] = [];
      let page = 1;
      for (;;) {
        const { data } = await api.get(`/messaging/conversations/?page=${page}`);
        all.push(...data.results);
        if (!data.next) break;
        page += 1;
      }
      return { results: all };
    },
  });

  const { data: messages } = useQuery<{ results: Message[] }>({
    queryKey: ['messages', selectedConv],
    // Follow every page: the history endpoint is paginated oldest-first, so reading
    // only page 1 hides all recent messages once a thread passes the page size.
    queryFn: async () => {
      const all: Message[] = [];
      let page = 1;
      for (;;) {
        const { data } = await api.get(`/messaging/messages/?conversation=${selectedConv}&page=${page}`);
        all.push(...data.results);
        if (!data.next) break;
        page += 1;
      }
      return { results: all };
    },
    enabled: !!selectedConv,
  });

  // Concerns the current user has already reported, so the "Reported" state
  // persists across reloads and the same message cannot be trivially re-reported.
  const { data: myReports } = useQuery<{ results: { id: number; message: number | null }[] }>({
    queryKey: ['my-abuse-reports'],
    queryFn: async () => {
      const all: { id: number; message: number | null }[] = [];
      let page = 1;
      for (;;) {
        const { data } = await api.get(`/messaging/abuse-reports/?page=${page}`);
        all.push(...data.results);
        if (!data.next) break;
        page += 1;
      }
      return { results: all };
    },
  });

  const reportedMessageIds = new Set<number>([
    ...(myReports?.results || [])
      .map(r => r.message)
      .filter((m): m is number => m != null),
    ...locallyReported,
  ]);

  // Applies an edit (own PATCH result, or another participant's edit relayed
  // over the WS message_edited event) to whichever store currently holds the
  // message - the react-query history cache, or the local WS buffer for
  // messages that haven't been folded into a refetch yet.
  const patchMessage = useCallback((id: number, fields: Partial<Message>) => {
    const cached = qc.getQueryData<{ results: Message[] }>(['messages', selectedConv]);
    if (cached?.results.some(m => m.id === id)) {
      qc.setQueryData<{ results: Message[] }>(['messages', selectedConv], (old) =>
        old ? { ...old, results: old.results.map(m => (m.id === id ? { ...m, ...fields } : m)) } : old
      );
    } else {
      setWsMessages(prev => prev.map(m => (m.id === id ? { ...m, ...fields } : m)));
    }
  }, [qc, selectedConv]);

  useEffect(() => {
    if (!selectedConv) return;
    const token = localStorage.getItem('access_token');
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/chat/${selectedConv}/?token=${token}`);
    wsRef.current = ws;
    setWsMessages([]);
    setModerationNotice(null);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chat_message') {
        // Live release of a previously flagged message (or a fresh delivered
        // send) - dedupe by message_id against whatever already holds this
        // id, whether that's the fetched history (react-query cache) or the
        // local WS buffer, and flip a matching flagged bubble to delivered
        // in place rather than appending a duplicate.
        const releasedId = data.message_id;
        const cached = qc.getQueryData<{ results: Message[] }>(['messages', selectedConv]);
        const cachedMsg = cached?.results.find(m => m.id === releasedId);
        if (cachedMsg) {
          if (cachedMsg.status !== 'delivered') {
            qc.setQueryData<{ results: Message[] }>(['messages', selectedConv], (old) =>
              old
                ? {
                    ...old,
                    results: old.results.map(m =>
                      m.id === releasedId
                        ? { ...m, status: 'delivered' as const, body: data.body, sent_at: data.sent_at }
                        : m
                    ),
                  }
                : old
            );
          }
        } else {
          setWsMessages(prev => {
            const idx = prev.findIndex(m => m.id === releasedId);
            if (idx !== -1) {
              const next = [...prev];
              next[idx] = { ...next[idx], status: 'delivered', body: data.body, sent_at: data.sent_at };
              return next;
            }
            return [...prev, {
              id: data.message_id, conversation: selectedConv,
              sender: data.sender_id, sender_name: data.sender_name,
              body: data.body, sent_at: data.sent_at,
              status: 'delivered', attachment: data.attachment_url ?? null,
              is_read: data.sender_id === user?.id,
            }];
          });
        }
        setModerationNotice(null);
      } else if (data.type === 'message_edited') {
        // Relayed edit of a delivered message (own edit reflected back, or the
        // other participant's edit when they have the thread open) - replace
        // the body/edited_at in place, never append.
        patchMessage(data.message_id, { body: data.body, edited_at: data.edited_at });
      } else if (data.type === 'message_flagged') {
        setModerationNotice({ type: 'flagged', text: composeFlaggedText(data.reason) });
        // The consumer persists the message but only sends back reason/id, not
        // the body - refetch history so the pending bubble appears (Task 5
        // already includes the sender's own flagged messages in the listing).
        if (data.message_id) qc.invalidateQueries({ queryKey: ['messages', selectedConv] });
      } else if (data.type === 'message_blocked') {
        // Two shapes share this event: genuine moderation blocks (message_id
        // present, `reason` a bare category fragment needing composition) and
        // account/relationship guards (no message_id, `reason` already a full
        // sentence) - never run the latter through the sentence composer.
        setModerationNotice({
          type: 'blocked',
          text: data.message_id
            ? composeBlockedText(data.reason)
            : (data.reason || 'Your message could not be sent as it contains restricted content.'),
        });
        if (data.message_id) qc.invalidateQueries({ queryKey: ['messages', selectedConv] });
      }
    };
    ws.onerror = () => {
      setModerationNotice({
        type: 'blocked',
        text: 'Connection error. Please refresh the page to continue messaging.',
      });
    };
    ws.onclose = (e) => {
      if (!e.wasClean) {
        setModerationNotice({
          type: 'blocked',
          text: 'Connection lost. Please refresh the page to continue messaging.',
        });
      }
    };
    return () => ws.close();
  }, [selectedConv, user?.id, patchMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, wsMessages]);

  // Restore (or clear) the per-conversation draft whenever the selected
  // conversation changes, including on first load after a reload/rotation.
  // Switching conversations always drops out of edit mode - the message
  // being edited belongs to the conversation being left.
  useEffect(() => {
    setDraft(selectedConv ? sessionStorage.getItem(draftKey(selectedConv)) ?? '' : '');
    setEditingMsgId(null);
    setEditDraft('');
    requestAnimationFrame(() => autoGrow());
  }, [selectedConv]);

  // Loads an existing message's body into the composer in "editing" mode.
  // Uses its own state (editDraft), so the in-progress new-message draft
  // (and its sessionStorage entry) is left completely untouched underneath.
  const startEditingMessage = (msg: Message) => {
    setEditingMsgId(msg.id);
    setEditDraft(msg.body);
    setModerationNotice(null);
    requestAnimationFrame(() => autoGrow());
  };

  const cancelEditingMessage = () => {
    setEditingMsgId(null);
    setEditDraft('');
    setModerationNotice(null);
    requestAnimationFrame(() => autoGrow());
  };

  const saveEditedMessage = async () => {
    const body = editDraft.trim();
    if (!body || editingMsgId == null) return;
    const id = editingMsgId;
    setModerationNotice(null);
    setIsSavingEdit(true);
    try {
      const resp = await api.patch(`/messaging/messages/${id}/`, { body });
      // A background refetch of this conversation's history (staleTime 30s +
      // refetchOnWindowFocus in App.tsx) may already be in flight from before
      // the PATCH was sent. If it resolves after our direct cache write below
      // it would silently revert the bubble to its pre-edit body - cancel it
      // first so it can't land, then invalidate so a fresh, post-edit fetch
      // replaces whatever that cancelled request left behind.
      await qc.cancelQueries({ queryKey: ['messages', selectedConv] });
      if (resp.status === 202) {
        // Held for re-review - the edit was accepted, so leave editing mode
        // (mirrors a fresh flagged send) and let the envelope's serialised
        // message drive the pending badge.
        const respData = resp.data as { moderation_reason?: string; message?: Message };
        setModerationNotice({ type: 'flagged', text: composeFlaggedText(respData.moderation_reason) });
        if (respData.message) patchMessage(id, respData.message);
        cancelEditingMessage();
      } else {
        patchMessage(id, resp.data as Message);
        cancelEditingMessage();
      }
      qc.invalidateQueries({ queryKey: ['messages', selectedConv] });
      qc.invalidateQueries({ queryKey: ['conversations'] });
    } catch (err: any) {
      await qc.cancelQueries({ queryKey: ['messages', selectedConv] });
      const errData = err?.response?.data as { detail?: string; moderation_reason?: string; message?: Message } | undefined;
      setModerationNotice({
        type: 'blocked',
        text: composeBlockedText(errData?.moderation_reason, errData?.detail),
      });
      if (errData?.message) patchMessage(id, errData.message);
      qc.invalidateQueries({ queryKey: ['messages', selectedConv] });
      // Stay in editing mode (mirrors a blocked fresh send keeping the draft)
      // so the sender can amend the offending text and resubmit.
    } finally {
      setIsSavingEdit(false);
    }
  };

  const sendMessage = async () => {
    const body = draft.trim();
    if (!body || !selectedConv) return;
    setDraft('');
    if (selectedConv) sessionStorage.removeItem(draftKey(selectedConv));
    if (taRef.current) taRef.current.style.height = 'auto';
    setModerationNotice(null);
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ body }));
      return;
    }
    // Socket not open yet (e.g. first message sent immediately after opening a
    // conversation) — fall back to REST so the message is persisted, not lost.
    try {
      const resp = await api.post('/messaging/messages/', { conversation: selectedConv, body });
      if (resp.status === 202) {
        const respData = resp.data as { moderation_reason?: string; message?: Message };
        setModerationNotice({ type: 'flagged', text: composeFlaggedText(respData.moderation_reason) });
        // Append the serialised message straight away so the pending bubble
        // appears instantly, without waiting for the refetch below.
        if (respData.message) setWsMessages(prev => [...prev, respData.message as Message]);
      }
      qc.invalidateQueries({ queryKey: ['messages', selectedConv] });
      qc.invalidateQueries({ queryKey: ['conversations'] });
    } catch (err: any) {
      const errData = err?.response?.data as { detail?: string; moderation_reason?: string; message?: Message } | undefined;
      setModerationNotice({
        type: 'blocked',
        text: composeBlockedText(errData?.moderation_reason, errData?.detail),
      });
      if (errData?.message) setWsMessages(prev => [...prev, errData.message as Message]);
      setDraft(body);
      if (selectedConv) sessionStorage.setItem(draftKey(selectedConv), body);
      // setDraft is async, so the textarea's value (and thus scrollHeight)
      // has not updated yet — defer the re-grow to the next frame.
      requestAnimationFrame(() => autoGrow());
    }
  };

  const sendAttachment = async (file: File) => {
    if (!selectedConv) return;
    setAttachPending(true);
    setModerationNotice(null);
    try {
      const fd = new FormData();
      fd.append('conversation', String(selectedConv));
      fd.append('body', file.name);
      fd.append('attachment', file);
      await api.post('/messaging/messages/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      qc.invalidateQueries({ queryKey: ['messages', selectedConv] });
    } catch (err: any) {
      setModerationNotice({
        type: 'blocked',
        text: err.response?.data?.attachment?.[0] ?? 'That file could not be attached.',
      });
    } finally {
      setAttachPending(false);
      if (attachRef.current) attachRef.current.value = '';
    }
  };

  const reportAbuse = useMutation({
    mutationFn: ({ messageId, senderId, description }: { messageId: number; senderId: number | null; description: string }) =>
      api.post('/messaging/abuse-reports/', {
        message: messageId,
        ...(senderId ? { reported_user: senderId } : {}),
        description,
      }),
    onSuccess: (_, { messageId }) => {
      setReportingMsgId(null);
      setReportingMsgSender(null);
      // Persist the reported state (no auto-revert) and refresh the server set.
      setLocallyReported(prev => new Set(prev).add(messageId));
      qc.invalidateQueries({ queryKey: ['my-abuse-reports'] });
    },
  });

  const allMessages = [
    ...(messages?.results || []),
    ...wsMessages.filter(wm => !(messages?.results || []).find(m => m.id === wm.id)),
  ];

  const selectedConvData = conversations?.results?.find(c => c.id === selectedConv);

  return (
    <div>
      {/* Page title */}
      <div className="mb-5">
        <h1 className="text-2xl font-extrabold text-navy-500">Messages</h1>
        <p className="text-sm text-navy-500/50 mt-0.5">
          All communications are moderated for safeguarding.
        </p>
      </div>

      <div className="h-[calc(100dvh-11rem)] md:h-[calc(100vh-14rem)] flex rounded-2xl overflow-hidden shadow-card border border-purple-100">
        {/* ── Sidebar ── */}
        <div className={`w-full md:w-72 bg-white border-r border-purple-100 flex-col md:flex-shrink-0 ${selectedConv ? 'hidden md:flex' : 'flex'}`}>
          <div className="px-4 py-3 border-b border-purple-100 bg-gradient-brand-pale">
            <p className="text-xs font-bold text-navy-500 uppercase tracking-widest">Conversations</p>
          </div>
          {(userHasRole(user, 'scholar') || userHasRole(user, 'mentor') || userHasRole(user, 'sponsor')) && (
            <div className="px-3 py-2.5 border-b border-purple-100 space-y-2">
              <button
                onClick={() => contactSupport.mutate()}
                disabled={contactSupport.isPending}
                className="w-full flex items-center gap-2 bg-gradient-brand-soft text-white text-xs font-bold px-3 py-2 rounded-xl hover:opacity-90 disabled:opacity-50 transition-all shadow-brand"
              >
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                {contactSupport.isPending ? 'Opening…' : 'Message Arkwright for Support'}
              </button>
              {userHasRole(user, 'scholar') && user?.scholar_profile?.sponsor && (
                <>
                  <button
                    onClick={() => contactSponsor.mutate(undefined)}
                    disabled={contactSponsor.isPending}
                    className="w-full flex items-center gap-2 bg-orange-500 text-white text-xs font-bold px-3 py-2 rounded-xl hover:opacity-90 disabled:opacity-50 transition-all"
                  >
                    <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    {contactSponsor.isPending ? 'Opening…' : 'Message my Sponsor'}
                  </button>
                  {sponsorError && (
                    <p className="text-[11px] text-red-500 px-1">{sponsorError}</p>
                  )}
                </>
              )}
            </div>
          )}
          {userHasRole(user, 'sponsor') && user?.sponsor_profile?.sponsored_scholars?.length ? (
            <div className="px-3 py-2.5 border-b border-purple-100">
              <p className="text-[10px] font-bold text-navy-500/40 uppercase tracking-widest mb-1.5">My Scholars</p>
              <div className="space-y-1.5">
                {user.sponsor_profile.sponsored_scholars.map(s => (
                  <button
                    key={s.id}
                    onClick={() => contactSponsor.mutate(s.id)}
                    disabled={contactSponsor.isPending}
                    className="w-full flex items-center gap-2 bg-orange-50 border border-orange-200 text-orange-700 text-xs font-semibold px-3 py-2 rounded-xl hover:bg-orange-100 disabled:opacity-50 transition-all"
                  >
                    <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                    {s.full_name}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
          <div className="flex-1 overflow-y-auto">
            {(!conversations?.results || conversations.results.length === 0) && (
              <p className="text-xs text-navy-500/40 p-4">No conversations yet.</p>
            )}
            {/* Direct / group / sponsor conversations */}
            {conversations?.results?.filter(c => c.conversation_type !== 'mass_message').map(conv => {
              const isActive = selectedConv === conv.id;
              const otherNames = conv.participant_names.filter(n => n !== user?.full_name).join(', ');
              return (
                <button
                  key={conv.id}
                  onClick={() => setSelectedConv(conv.id)}
                  className={`w-full text-left px-4 py-3.5 border-b border-purple-50 transition-all ${
                    isActive
                      ? 'bg-gradient-brand-pale border-l-4 border-l-pink-500'
                      : 'hover:bg-purple-50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <p className={`text-sm font-semibold truncate ${isActive ? 'text-pink-500' : 'text-navy-500'}`}>
                      {conv.subject || otherNames || 'Conversation'}
                    </p>
                    {conv.unread_count > 0 && (
                      <span className="ml-1 flex-shrink-0 bg-gradient-brand-soft text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                  {conv.last_message && (
                    <p className="text-xs text-navy-500/40 mt-0.5 truncate">{conv.last_message.body}</p>
                  )}
                </button>
              );
            })}
            {/* Announcements (mass messages from Arkwright) — shown separately */}
            {conversations?.results?.some(c => c.conversation_type === 'mass_message') && (
              <>
                <div className="px-4 py-2 bg-purple-50 border-b border-purple-100">
                  <p className="text-[10px] font-bold text-navy-500/40 uppercase tracking-widest">Announcements</p>
                </div>
                {conversations.results.filter(c => c.conversation_type === 'mass_message').map(conv => {
                  const isActive = selectedConv === conv.id;
                  return (
                    <button
                      key={conv.id}
                      onClick={() => setSelectedConv(conv.id)}
                      className={`w-full text-left px-4 py-3.5 border-b border-purple-50 transition-all ${
                        isActive
                          ? 'bg-gradient-brand-pale border-l-4 border-l-pink-500'
                          : 'hover:bg-purple-50'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <p className={`text-sm font-semibold truncate ${isActive ? 'text-pink-500' : 'text-navy-500'}`}>
                          {conv.subject || 'Announcement'}
                        </p>
                        {conv.unread_count > 0 && (
                          <span className="ml-1 flex-shrink-0 bg-gradient-brand-soft text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                            {conv.unread_count}
                          </span>
                        )}
                      </div>
                      {conv.last_message && (
                        <p className="text-xs text-navy-500/40 mt-0.5 truncate">{conv.last_message.body}</p>
                      )}
                    </button>
                  );
                })}
              </>
            )}
          </div>
        </div>

        {/* ── Chat thread ── */}
        <div className={`flex-1 min-w-0 flex-col bg-[#faf9fd] ${selectedConv ? 'flex' : 'hidden md:flex'}`}>
          {selectedConv ? (
            <>
              {/* Thread header */}
              <div className="px-5 py-3 bg-white border-b border-purple-100 flex items-center justify-between">
                <div className="flex items-center min-w-0">
                  <button
                    onClick={() => setSelectedConv(null)}
                    className="md:hidden mr-2 p-2 -ml-2 rounded-lg text-navy-500/60 hover:bg-purple-50"
                    aria-label="Back to conversations"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                  </button>
                  <div className="min-w-0">
                    <p className="font-bold text-sm text-navy-500 truncate">
                      {selectedConvData?.subject ||
                        selectedConvData?.participant_names.filter(n => n !== user?.full_name).join(', ') ||
                        'Conversation'}
                    </p>
                    <p className="text-[11px] text-navy-500/40 truncate">
                      {selectedConvData?.participant_names.join(', ')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                  {selectedConvData?.conversation_type !== 'mass_message' && (
                    <Link
                      to="/profile#documents"
                      title="Shared documents"
                      aria-label="Shared documents"
                      className="flex items-center gap-1 text-xs font-semibold text-purple-500 hover:text-pink-500 transition-colors"
                    >
                      <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <span className="hidden sm:inline">Shared documents</span>
                    </Link>
                  )}
                  <span className="text-[10px] bg-purple-100 text-purple-700 font-semibold px-2 py-1 rounded-full uppercase tracking-wider">
                    Moderated
                  </span>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto overflow-x-hidden px-5 py-4 space-y-3">
                {allMessages.map((msg, idx) => {
                  const isMine = msg.sender === user?.id;
                  const reported = reportedMessageIds.has(msg.id);
                  const editable = isMessageEditable(msg, isMine, selectedConvData?.conversation_type);
                  const prevMsg = idx > 0 ? allMessages[idx - 1] : null;
                  const showDaySeparator = !prevMsg || new Date(prevMsg.sent_at).toDateString() !== new Date(msg.sent_at).toDateString();
                  return (
                    <React.Fragment key={`${msg.id}-${msg.sent_at}`}>
                    {showDaySeparator && (
                      <div className="flex justify-center">
                        <span className="bg-purple-50 text-navy-500/50 text-[11px] rounded-full px-3 py-1">
                          {dayLabel(msg.sent_at)}
                        </span>
                      </div>
                    )}
                    <div className={`flex min-w-0 ${isMine ? 'justify-end' : 'justify-start'}`}>
                      <div className="max-w-[80%] sm:max-w-sm min-w-0 group relative">
                        {!isMine && (
                          <p className="text-[11px] font-semibold text-purple-500 mb-1 ml-1">{msg.sender_name}</p>
                        )}
                        <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words min-w-0 ${
                          isMine
                            ? 'bg-gradient-brand-soft text-white rounded-br-sm shadow-brand'
                            : 'bg-white text-navy-500 rounded-bl-sm shadow-card'
                        }`}>
                          {msg.attachment ? (
                            <a
                              href={msg.attachment}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`flex items-center gap-1.5 underline text-xs font-semibold ${isMine ? 'text-white/90' : 'text-purple-600'}`}
                            >
                              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                              </svg>
                              {msg.body}
                            </a>
                          ) : msg.is_broadcast ? (
                            // is_broadcast (MessageSerializer.get_is_broadcast) is an
                            // identity-based backend flag, not a position guess: true
                            // only for the system-authored MassMessage body, which is
                            // the only body of this shape the backend has run through
                            // sanitise_rich_text(). Deliberately NOT keyed off
                            // conversation_type/index - a reply loaded via a WS race
                            // before REST history resolves, or a second human
                            // participant in the thread, would otherwise land at
                            // "index 0" and render unsanitised text as HTML. Replies
                            // (including from Arkwright via the admin reply panel) are
                            // ordinary chat messages and stay on the plain-text path
                            // below. WS chat_message events never carry is_broadcast,
                            // which defaults to undefined/falsy there - safe, because a
                            // broadcast message is only ever created server-side and
                            // only ever reaches the frontend via the REST history load.
                            <RichText body={msg.body} />
                          ) : (
                            <p className="whitespace-pre-wrap break-words">{msg.body}</p>
                          )}
                          {isMine && msg.status === 'flagged' && (
                            <span className="inline-flex items-center gap-1 mt-1.5 rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-semibold text-amber-600">
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Pending review
                            </span>
                          )}
                          {isMine && msg.status === 'blocked' && (
                            <span className="inline-flex items-center gap-1 mt-1.5 rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-semibold text-red-600">
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636L5.636 18.364M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Not delivered
                            </span>
                          )}
                        </div>
                        <div className={`flex items-center mt-1 gap-2 ${isMine ? 'justify-end' : 'justify-start'}`}>
                          <p className="text-[10px] text-navy-500/30" title={new Date(msg.sent_at).toLocaleString('en-GB')}>
                            {new Date(msg.sent_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                            {msg.edited_at && ' (edited)'}
                          </p>
                          {editable && (
                            <button
                              onClick={() => startEditingMessage(msg)}
                              title="Edit this message"
                              aria-label="Edit this message"
                              className="flex items-center justify-center w-10 h-10 -m-1.5 text-navy-500/40 hover:text-purple-500 transition-colors rounded-full hover:bg-purple-50"
                            >
                              <PencilIcon />
                            </button>
                          )}
                          {!isMine && (
                            reported ? (
                              <span className="text-[10px] text-green-600 font-semibold flex items-center gap-1">
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                </svg>
                                Reported
                              </span>
                            ) : (
                              <button
                                onClick={() => { setReportingMsgId(msg.id); setReportingMsgSender(msg.sender); }}
                                title="Report a concern about this message"
                                className="flex items-center gap-1 text-[10px] text-red-400 hover:text-red-600 font-semibold transition-all px-1.5 py-0.5 rounded hover:bg-red-50 border border-red-100"
                              >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                                </svg>
                                Report a Concern
                              </button>
                            )
                          )}
                        </div>
                      </div>
                    </div>
                    </React.Fragment>
                  );
                })}

                {/* Report confirmation modal */}
                {reportingMsgId !== null && (
                  <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl shadow-xl p-6 w-80 mx-4">
                      <h3 className="font-bold text-navy-500 mb-1">Report a Concern</h3>
                      <p className="text-xs text-navy-500/50 mb-4">This will be reviewed by our moderation team within 24 hours or next working day. If you have any immediate safeguarding concerns please call 01926 333200.</p>
                      <ReportForm
                        onSubmit={(desc) => reportAbuse.mutate({ messageId: reportingMsgId, senderId: reportingMsgSender, description: desc })}
                        onCancel={() => { setReportingMsgId(null); setReportingMsgSender(null); }}
                        isPending={reportAbuse.isPending}
                      />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Compose */}
              <div className="px-5 py-3 bg-white border-t border-purple-100">
                {/* Editing banner */}
                {editingMsgId !== null && (
                  <div className="mb-2.5 px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-between gap-2 bg-purple-50 border border-purple-100 text-purple-700">
                    <span className="flex items-center gap-1.5">
                      <PencilIcon className="w-3.5 h-3.5 flex-shrink-0" />
                      Editing message
                    </span>
                    <button
                      onClick={cancelEditingMessage}
                      className="font-semibold text-navy-500/50 hover:text-navy-500 underline"
                    >
                      Cancel
                    </button>
                  </div>
                )}
                {/* Moderation notices */}
                {moderationNotice && (
                  <div className={`mb-2.5 px-3 py-2 rounded-lg text-xs font-medium flex items-start gap-2 ${
                    moderationNotice.type === 'blocked'
                      ? 'bg-red-50 border border-red-100 text-red-600'
                      : 'bg-yellow-50 border border-yellow-100 text-yellow-700'
                  }`}>
                    <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                    </svg>
                    {moderationNotice.text}
                  </div>
                )}
                {selectedConvData?.replies_enabled === false ? (
                  <div className="text-xs text-navy-500/40 text-center py-2 italic">
                    Replies are disabled for this broadcast message.
                  </div>
                ) : (
                  <div className="flex items-end gap-2">
                    {/* Hidden file input for attachments */}
                    <input
                      ref={attachRef}
                      type="file"
                      className="hidden"
                      accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip"
                      onChange={e => { const f = e.target.files?.[0]; if (f) sendAttachment(f); }}
                    />
                    <button
                      type="button"
                      onClick={() => attachRef.current?.click()}
                      disabled={attachPending || editingMsgId !== null}
                      title={editingMsgId !== null ? 'Cancel editing to attach a file' : 'Attach a file'}
                      className="flex-shrink-0 text-navy-500/40 hover:text-purple-500 disabled:opacity-40 transition-colors p-1"
                    >
                      {attachPending ? (
                        <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10" strokeWidth={2} strokeDasharray="40" strokeDashoffset="10" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                        </svg>
                      )}
                    </button>
                    <textarea
                      ref={taRef}
                      rows={1}
                      value={editingMsgId !== null ? editDraft : draft}
                      onChange={e => {
                        if (editingMsgId !== null) {
                          setEditDraft(e.target.value);
                        } else {
                          setDraft(e.target.value);
                          if (selectedConv) sessionStorage.setItem(draftKey(selectedConv), e.target.value);
                        }
                        autoGrow();
                      }}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && !e.shiftKey && !IS_COARSE_POINTER) {
                          e.preventDefault();
                          if (editingMsgId !== null) {
                            if (!isSavingEdit) saveEditedMessage();
                          } else {
                            sendMessage();
                          }
                        }
                      }}
                      placeholder={editingMsgId !== null ? 'Edit your message...' : 'Type a message...'}
                      className="flex-1 min-w-0 resize-none overflow-y-auto max-h-40 border-2 border-purple-100 rounded-xl px-4 py-2.5 text-sm text-navy-500 bg-[#faf9fd] focus:outline-none focus:border-pink-500 transition-colors placeholder:text-navy-500/30"
                    />
                    {editingMsgId !== null ? (
                      <button
                        onClick={saveEditedMessage}
                        disabled={!editDraft.trim() || isSavingEdit}
                        className="flex-shrink-0 bg-gradient-brand-soft text-white px-4 py-2.5 rounded-xl text-sm font-bold hover:opacity-90 disabled:opacity-40 transition-all shadow-brand flex items-center gap-1.5"
                      >
                        {isSavingEdit ? 'Saving…' : 'Save'}
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                      </button>
                    ) : (
                      <button
                        onClick={sendMessage}
                        disabled={!draft.trim()}
                        className="flex-shrink-0 bg-gradient-brand-soft text-white px-4 py-2.5 rounded-xl text-sm font-bold hover:opacity-90 disabled:opacity-40 transition-all shadow-brand flex items-center gap-1.5"
                      >
                        Send
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-navy-500/30">
              <svg className="w-14 h-14 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p className="text-sm font-medium">Select a conversation</p>
              <p className="text-xs mt-1">Your messages will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
