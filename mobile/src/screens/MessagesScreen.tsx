import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, ActivityIndicator, KeyboardAvoidingView, Platform, RefreshControl,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../hooks/api';
import { useAuth } from '../hooks/useAuth';
import type { Conversation, Message } from '../types';

function ConversationItem({ conv, onPress }: { conv: Conversation; onPress: () => void }) {
  const { user } = useAuth();
  const other = conv.participants.find(p => p.id !== user?.id);
  const initials = other ? `${other.first_name[0]}${other.last_name[0]}` : '?';

  return (
    <TouchableOpacity style={styles.convItem} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{initials}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <View style={styles.convHeader}>
          <Text style={styles.convName}>{other?.full_name ?? 'Unknown'}</Text>
          {conv.last_message && (
            <Text style={styles.convTime}>
              {new Date(conv.last_message.sent_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
            </Text>
          )}
        </View>
        <Text style={styles.convPreview} numberOfLines={1}>
          {conv.last_message?.content ?? 'No messages yet'}
        </Text>
      </View>
      {conv.unread_count > 0 && (
        <View style={styles.unreadBadge}>
          <Text style={styles.unreadText}>{conv.unread_count}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

function MessageThread({ convId, onBack }: { convId: number; onBack: () => void }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [text, setText] = useState('');
  const scrollRef = useRef<ScrollView>(null);

  const { data: messages = [], isLoading } = useQuery<Message[]>({
    queryKey: ['messages', convId],
    queryFn: () => api.get(`/messaging/conversations/${convId}/messages/`).then(r => r.data.results ?? r.data),
    refetchInterval: 5000,
  });

  const send = useMutation({
    mutationFn: (content: string) => api.post(`/messaging/conversations/${convId}/messages/`, { content }),
    onSuccess: () => {
      setText('');
      qc.invalidateQueries({ queryKey: ['messages', convId] });
    },
  });

  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: false }), 100);
  }, [messages.length]);

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <View style={styles.threadHeader}>
        <TouchableOpacity onPress={onBack} style={{ padding: 4 }}>
          <Text style={{ color: '#9333ea', fontWeight: '600', fontSize: 15 }}>← Back</Text>
        </TouchableOpacity>
      </View>

      {isLoading ? <ActivityIndicator color="#9333ea" style={{ flex: 1 }} /> : (
        <ScrollView ref={scrollRef} style={{ flex: 1 }} contentContainerStyle={{ padding: 16, paddingBottom: 8 }}>
          {messages.map(m => {
            const mine = m.sender.id === user?.id;
            return (
              <View key={m.id} style={[styles.bubble, mine ? styles.bubbleMine : styles.bubbleTheirs]}>
                {!mine && <Text style={styles.bubbleSender}>{m.sender.first_name}</Text>}
                <Text style={[styles.bubbleText, mine && { color: '#fff' }]}>{m.content}</Text>
                <Text style={[styles.bubbleTime, mine && { color: 'rgba(255,255,255,0.6)' }]}>
                  {new Date(m.sent_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
            );
          })}
        </ScrollView>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={styles.messageInput}
          value={text}
          onChangeText={setText}
          placeholder="Type a message..."
          placeholderTextColor="#94a3b8"
          multiline
          maxLength={1000}
        />
        <TouchableOpacity
          style={[styles.sendBtn, !text.trim() && { opacity: 0.4 }]}
          onPress={() => text.trim() && send.mutate(text.trim())}
          disabled={!text.trim() || send.isPending}
        >
          <Text style={styles.sendBtnText}>→</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

export default function MessagesScreen() {
  const [activeConv, setActiveConv] = useState<number | null>(null);
  const { data: conversations = [], isLoading, refetch } = useQuery<Conversation[]>({
    queryKey: ['conversations'],
    queryFn: () => api.get('/messaging/conversations/').then(r => r.data.results ?? r.data),
    refetchInterval: 10_000,
  });

  if (activeConv !== null) {
    return (
      <View style={{ flex: 1, backgroundColor: '#f8f7fc' }}>
        <MessageThread convId={activeConv} onBack={() => setActiveConv(null)} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {isLoading ? (
        <ActivityIndicator color="#9333ea" style={{ marginTop: 40 }} />
      ) : (
        <ScrollView
          refreshControl={<RefreshControl refreshing={false} onRefresh={refetch} tintColor="#9333ea" />}
        >
          {conversations.length === 0 ? (
            <View style={styles.empty}>
              <Text style={styles.emptyIcon}>💬</Text>
              <Text style={styles.emptyText}>No conversations yet</Text>
            </View>
          ) : (
            conversations.map(c => (
              <ConversationItem key={c.id} conv={c} onPress={() => setActiveConv(c.id)} />
            ))
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f7fc' },

  convItem: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 14,
    borderBottomWidth: 1, borderBottomColor: '#f3e8ff',
  },
  avatar: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: '#9333ea', alignItems: 'center', justifyContent: 'center',
  },
  avatarText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  convHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 },
  convName: { fontWeight: '700', color: '#1e1b4b', fontSize: 14 },
  convTime: { fontSize: 11, color: '#94a3b8' },
  convPreview: { fontSize: 12, color: '#94a3b8' },
  unreadBadge: {
    backgroundColor: '#ec4899', borderRadius: 10, minWidth: 20, height: 20,
    alignItems: 'center', justifyContent: 'center', paddingHorizontal: 5,
  },
  unreadText: { color: '#fff', fontSize: 10, fontWeight: '700' },

  threadHeader: {
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: '#f3e8ff',
  },

  bubble: { maxWidth: '80%', marginBottom: 10, borderRadius: 16, padding: 12 },
  bubbleMine: { alignSelf: 'flex-end', backgroundColor: '#9333ea', borderBottomRightRadius: 4 },
  bubbleTheirs: { alignSelf: 'flex-start', backgroundColor: '#fff', borderBottomLeftRadius: 4, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 1 },
  bubbleSender: { fontSize: 11, fontWeight: '600', color: '#9333ea', marginBottom: 3 },
  bubbleText: { fontSize: 14, color: '#1e1b4b', lineHeight: 20 },
  bubbleTime: { fontSize: 10, color: '#94a3b8', marginTop: 4, textAlign: 'right' },

  inputRow: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    backgroundColor: '#fff', paddingHorizontal: 12, paddingVertical: 10,
    borderTopWidth: 1, borderTopColor: '#f3e8ff',
  },
  messageInput: {
    flex: 1, borderWidth: 1, borderColor: '#e8e3f5', borderRadius: 20,
    paddingHorizontal: 14, paddingVertical: 10, fontSize: 14, color: '#1e1b4b',
    maxHeight: 100, backgroundColor: '#fafafa',
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#9333ea', alignItems: 'center', justifyContent: 'center',
  },
  sendBtnText: { color: '#fff', fontSize: 18, fontWeight: '700' },

  empty: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 36, marginBottom: 10 },
  emptyText: { color: '#1e1b4b', opacity: 0.4, fontSize: 14 },
});
