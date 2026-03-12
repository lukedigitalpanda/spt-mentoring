import React from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../hooks/api';
import type { Notification } from '../types';

const NOTIF_ICONS: Record<string, string> = {
  session_request: '📅',
  session_confirmed: '✅',
  session_cancelled: '❌',
  session_reminder: '⏰',
  session_feedback: '⭐',
  message: '💬',
  match: '🤝',
  forum_reply: '💭',
  survey: '📊',
  goal: '🎯',
  system: '🔔',
};

function fmtAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function NotificationItem({ notif, onMarkRead }: { notif: Notification; onMarkRead: (id: number) => void }) {
  return (
    <TouchableOpacity
      style={[styles.item, !notif.is_read && styles.itemUnread]}
      onPress={() => !notif.is_read && onMarkRead(notif.id)}
      activeOpacity={0.8}
    >
      <Text style={styles.icon}>{NOTIF_ICONS[notif.notification_type] ?? '🔔'}</Text>
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>{notif.title}</Text>
        <Text style={styles.body} numberOfLines={2}>{notif.body}</Text>
        <Text style={styles.time}>{fmtAgo(notif.created_at)}</Text>
      </View>
      {!notif.is_read && <View style={styles.unreadDot} />}
    </TouchableOpacity>
  );
}

export default function NotificationsScreen() {
  const qc = useQueryClient();

  const { data: notifications = [], isLoading, refetch } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: () => api.get('/notifications/').then(r => r.data.results ?? r.data),
  });

  const markRead = useMutation({
    mutationFn: (id: number) => api.post(`/notifications/${id}/mark_read/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAll = useMutation({
    mutationFn: () => api.post('/notifications/mark_all_read/'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const hasUnread = notifications.some(n => !n.is_read);

  return (
    <View style={styles.container}>
      {hasUnread && (
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => markAll.mutate()} disabled={markAll.isPending}>
            <Text style={styles.markAllBtn}>Mark all as read</Text>
          </TouchableOpacity>
        </View>
      )}

      {isLoading ? (
        <ActivityIndicator color="#9333ea" style={{ marginTop: 40 }} />
      ) : (
        <ScrollView
          refreshControl={<RefreshControl refreshing={false} onRefresh={refetch} tintColor="#9333ea" />}
        >
          {notifications.length === 0 ? (
            <View style={styles.empty}>
              <Text style={styles.emptyIcon}>🔔</Text>
              <Text style={styles.emptyText}>No notifications yet</Text>
            </View>
          ) : (
            notifications.map(n => (
              <NotificationItem key={n.id} notif={n} onMarkRead={(id) => markRead.mutate(id)} />
            ))
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f7fc' },
  topBar: {
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: '#f3e8ff', alignItems: 'flex-end',
  },
  markAllBtn: { color: '#9333ea', fontWeight: '600', fontSize: 13 },

  item: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 12,
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 14,
    borderBottomWidth: 1, borderBottomColor: '#f9f7ff',
  },
  itemUnread: { backgroundColor: '#fdf8ff' },
  icon: { fontSize: 22, marginTop: 1 },
  title: { fontSize: 14, fontWeight: '700', color: '#1e1b4b', marginBottom: 2 },
  body: { fontSize: 12, color: '#1e1b4b', opacity: 0.6, lineHeight: 17 },
  time: { fontSize: 11, color: '#94a3b8', marginTop: 4 },
  unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#ec4899', marginTop: 6 },

  empty: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 36, marginBottom: 10 },
  emptyText: { color: '#1e1b4b', opacity: 0.4, fontSize: 14 },
});
