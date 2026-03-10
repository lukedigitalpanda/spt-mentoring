import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { Conversation, Message } from '../types';

export default function MessagesPage() {
  const { user } = useAuth();
  const [selectedConv, setSelectedConv] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [wsMessages, setWsMessages] = useState<Message[]>([]);

  const { data: conversations } = useQuery<{ results: Conversation[] }>({
    queryKey: ['conversations'],
    queryFn: () => api.get('/messaging/conversations/').then(r => r.data),
  });

  const { data: messages } = useQuery<{ results: Message[] }>({
    queryKey: ['messages', selectedConv],
    queryFn: () => api.get(`/messaging/messages/?conversation=${selectedConv}`).then(r => r.data),
    enabled: !!selectedConv,
  });

  useEffect(() => {
    if (!selectedConv) return;
    const token = localStorage.getItem('access_token');
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${selectedConv}/?token=${token}`);
    wsRef.current = ws;
    setWsMessages([]);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chat_message') {
        setWsMessages(prev => [...prev, {
          id: data.message_id, conversation: selectedConv,
          sender: data.sender_id, sender_name: data.sender_name,
          body: data.body, sent_at: data.sent_at,
          status: 'delivered', attachment: null,
          is_read: data.sender_id === user?.id,
        }]);
      }
    };
    return () => ws.close();
  }, [selectedConv, user?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, wsMessages]);

  const sendMessage = () => {
    if (!draft.trim() || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ body: draft }));
    setDraft('');
  };

  const reportAbuse = useMutation({
    mutationFn: (messageId: number) =>
      api.post('/messaging/abuse-reports/', { message: messageId, description: 'User reported this message' }),
    onSuccess: () => alert('Report submitted. Our team will review it.'),
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
        <h1 className="text-2xl font-extrabold text-navy-DEFAULT">Messages</h1>
        <p className="text-sm text-navy-DEFAULT/50 mt-0.5">
          All communications are moderated for safeguarding.
        </p>
      </div>

      <div className="h-[calc(100vh-14rem)] flex rounded-2xl overflow-hidden shadow-card border border-purple-100">
        {/* ── Sidebar ── */}
        <div className="w-72 bg-white border-r border-purple-100 flex flex-col flex-shrink-0">
          <div className="px-4 py-3 border-b border-purple-100 bg-gradient-brand-pale">
            <p className="text-xs font-bold text-navy-DEFAULT uppercase tracking-widest">Conversations</p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {(!conversations?.results || conversations.results.length === 0) && (
              <p className="text-xs text-navy-DEFAULT/40 p-4">No conversations yet.</p>
            )}
            {conversations?.results?.map(conv => {
              const isActive = selectedConv === conv.id;
              const otherNames = conv.participant_names.filter(n => n !== user?.full_name).join(', ');
              return (
                <button
                  key={conv.id}
                  onClick={() => setSelectedConv(conv.id)}
                  className={`w-full text-left px-4 py-3.5 border-b border-purple-50 transition-all ${
                    isActive
                      ? 'bg-gradient-brand-pale border-l-4 border-l-pink-DEFAULT'
                      : 'hover:bg-purple-50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <p className={`text-sm font-semibold truncate ${isActive ? 'text-pink-DEFAULT' : 'text-navy-DEFAULT'}`}>
                      {conv.subject || otherNames || 'Conversation'}
                    </p>
                    {conv.unread_count > 0 && (
                      <span className="ml-1 flex-shrink-0 bg-gradient-brand-soft text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                  {conv.last_message && (
                    <p className="text-xs text-navy-DEFAULT/40 mt-0.5 truncate">{conv.last_message.body}</p>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Chat thread ── */}
        <div className="flex-1 flex flex-col bg-[#faf9fd]">
          {selectedConv ? (
            <>
              {/* Thread header */}
              <div className="px-5 py-3 bg-white border-b border-purple-100 flex items-center justify-between">
                <div>
                  <p className="font-bold text-sm text-navy-DEFAULT">
                    {selectedConvData?.subject ||
                      selectedConvData?.participant_names.filter(n => n !== user?.full_name).join(', ') ||
                      'Conversation'}
                  </p>
                  <p className="text-[11px] text-navy-DEFAULT/40">
                    {selectedConvData?.participant_names.join(', ')}
                  </p>
                </div>
                <span className="text-[10px] bg-purple-100 text-purple-700 font-semibold px-2 py-1 rounded-full uppercase tracking-wider">
                  Moderated
                </span>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                {allMessages.map((msg) => {
                  const isMine = msg.sender === user?.id;
                  return (
                    <div key={`${msg.id}-${msg.sent_at}`} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-sm group relative ${isMine ? '' : ''}`}>
                        {!isMine && (
                          <p className="text-[11px] font-semibold text-purple-DEFAULT mb-1 ml-1">{msg.sender_name}</p>
                        )}
                        <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                          isMine
                            ? 'bg-gradient-brand-soft text-white rounded-br-sm shadow-brand'
                            : 'bg-white text-navy-DEFAULT rounded-bl-sm shadow-card'
                        }`}>
                          {msg.body}
                        </div>
                        <p className={`text-[10px] mt-1 ${isMine ? 'text-right text-navy-DEFAULT/30' : 'text-navy-DEFAULT/30'}`}>
                          {new Date(msg.sent_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                        {!isMine && (
                          <button
                            onClick={() => reportAbuse.mutate(msg.id)}
                            className="absolute -bottom-4 right-0 hidden group-hover:flex text-[10px] text-pink-DEFAULT hover:text-pink-600 font-semibold items-center gap-0.5"
                          >
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 7l2.55 2.4A1 1 0 0116 11H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" /></svg>
                            Report
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Compose */}
              <div className="px-5 py-3 bg-white border-t border-purple-100">
                <div className="flex items-end gap-2">
                  <input
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
                    placeholder="Type a message…"
                    className="flex-1 border-2 border-purple-100 rounded-xl px-4 py-2.5 text-sm text-navy-DEFAULT bg-[#faf9fd] focus:outline-none focus:border-pink-DEFAULT transition-colors placeholder:text-navy-DEFAULT/30"
                  />
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
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-navy-DEFAULT/30">
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
