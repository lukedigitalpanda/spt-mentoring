import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';
import { useAuth } from '../hooks/useAuth';
import type { Conversation, Message } from '../types';

export default function MessagesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
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

  // WebSocket for real-time chat
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
          id: data.message_id,
          conversation: selectedConv,
          sender: data.sender_id,
          sender_name: data.sender_name,
          body: data.body,
          sent_at: data.sent_at,
          status: 'delivered',
          attachment: null,
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

  return (
    <div className="h-[calc(100vh-12rem)] flex border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
      {/* Conversation list */}
      <div className="w-72 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Messages</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations?.results?.map(conv => (
            <button
              key={conv.id}
              onClick={() => setSelectedConv(conv.id)}
              className={`w-full text-left p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors ${selectedConv === conv.id ? 'bg-blue-50' : ''}`}
            >
              <div className="flex justify-between items-start">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {conv.subject || conv.participant_names.filter(n => n !== user?.full_name).join(', ')}
                </p>
                {conv.unread_count > 0 && (
                  <span className="ml-1 bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                    {conv.unread_count}
                  </span>
                )}
              </div>
              {conv.last_message && (
                <p className="text-xs text-gray-500 mt-1 truncate">{conv.last_message.body}</p>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Message thread */}
      <div className="flex-1 flex flex-col">
        {selectedConv ? (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {allMessages.map((msg) => (
                <div
                  key={`${msg.id}-${msg.sent_at}`}
                  className={`flex ${msg.sender === user?.id ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-md group relative ${msg.sender === user?.id ? 'order-2' : ''}`}>
                    {msg.sender !== user?.id && (
                      <p className="text-xs text-gray-500 mb-1">{msg.sender_name}</p>
                    )}
                    <div
                      className={`rounded-lg px-4 py-2 text-sm ${
                        msg.sender === user?.id
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      {msg.body}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(msg.sent_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                    {msg.sender !== user?.id && (
                      <button
                        onClick={() => reportAbuse.mutate(msg.id)}
                        className="absolute -bottom-4 right-0 hidden group-hover:flex text-xs text-red-500 hover:text-red-700"
                      >
                        Report
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            <div className="p-4 border-t border-gray-200">
              <div className="flex space-x-2">
                <input
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
                  placeholder="Type a message..."
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={sendMessage}
                  disabled={!draft.trim()}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  Send
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p className="text-sm">Select a conversation to start messaging</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
