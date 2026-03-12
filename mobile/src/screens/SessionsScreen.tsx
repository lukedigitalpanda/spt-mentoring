import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Linking, RefreshControl,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import api from '../hooks/api';
import { useAuth } from '../hooks/useAuth';
import type { MentoringSession } from '../types';

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  confirmed: '#22c55e',
  cancelled: '#ef4444',
  completed: '#6b7280',
  no_show: '#ef4444',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending', confirmed: 'Confirmed',
  cancelled: 'Cancelled', completed: 'Completed', no_show: 'No Show',
};

function SessionCard({ session }: { session: MentoringSession }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isMentor = user?.role === 'mentor';

  const confirm = useMutation({
    mutationFn: () => api.post(`/sessions/sessions/${session.id}/confirm/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
  const cancel = useMutation({
    mutationFn: () => api.post(`/sessions/sessions/${session.id}/cancel/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });

  const start = new Date(session.start_time);
  const dateStr = start.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
  const timeStr = start.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{session.title}</Text>
        <View style={[styles.badge, { backgroundColor: STATUS_COLORS[session.status] + '20' }]}>
          <Text style={[styles.badgeText, { color: STATUS_COLORS[session.status] }]}>
            {STATUS_LABELS[session.status]}
          </Text>
        </View>
      </View>

      <Text style={styles.cardMeta}>{dateStr} · {timeStr} ({session.duration_minutes} min)</Text>
      <Text style={styles.cardMeta}>
        {isMentor ? `Scholar: ${session.scholar.full_name}` : `Mentor: ${session.mentor.full_name}`}
      </Text>

      <View style={styles.cardActions}>
        {session.status === 'confirmed' && session.is_upcoming && (
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: '#22c55e' }]}
            onPress={() => Linking.openURL(session.jitsi_room_url)}
          >
            <Ionicons name="videocam" size={14} color="#fff" />
            <Text style={styles.actionBtnText}>Join</Text>
          </TouchableOpacity>
        )}
        {session.status === 'pending' && isMentor && (
          <>
            <TouchableOpacity
              style={[styles.actionBtn, { backgroundColor: '#9333ea' }]}
              onPress={() => confirm.mutate()}
              disabled={confirm.isPending}
            >
              <Text style={styles.actionBtnText}>Confirm</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionBtn, { backgroundColor: '#ef4444' }]}
              onPress={() => cancel.mutate()}
              disabled={cancel.isPending}
            >
              <Text style={styles.actionBtnText}>Decline</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
}

export default function SessionsScreen() {
  const [tab, setTab] = useState<'upcoming' | 'past'>('upcoming');

  const { data: sessions = [], isLoading, refetch } = useQuery<MentoringSession[]>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/sessions/sessions/').then(r => r.data.results ?? r.data),
  });

  const upcoming = sessions.filter(s => s.is_upcoming && s.status !== 'cancelled');
  const past = sessions.filter(s => !s.is_upcoming || s.status === 'completed');

  const displayed = tab === 'upcoming' ? upcoming : past;

  return (
    <View style={styles.container}>
      {/* Tabs */}
      <View style={styles.tabs}>
        {(['upcoming', 'past'] as const).map(t => (
          <TouchableOpacity key={t} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t === 'upcoming' ? 'Upcoming' : 'Past'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {isLoading ? (
        <ActivityIndicator color="#9333ea" style={{ marginTop: 40 }} />
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
          refreshControl={<RefreshControl refreshing={false} onRefresh={refetch} tintColor="#9333ea" />}
        >
          {displayed.length === 0 ? (
            <View style={styles.empty}>
              <Text style={styles.emptyIcon}>📅</Text>
              <Text style={styles.emptyText}>No {tab} sessions</Text>
            </View>
          ) : (
            displayed.map(s => <SessionCard key={s.id} session={s} />)
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f7fc' },
  tabs: { flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f3e8ff' },
  tab: { flex: 1, paddingVertical: 14, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#9333ea' },
  tabText: { fontSize: 13, fontWeight: '600', color: '#94a3b8' },
  tabTextActive: { color: '#9333ea' },

  card: {
    backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 12,
    shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 6 },
  cardTitle: { flex: 1, fontSize: 14, fontWeight: '700', color: '#1e1b4b' },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 20 },
  badgeText: { fontSize: 10, fontWeight: '700' },
  cardMeta: { fontSize: 12, color: '#1e1b4b', opacity: 0.5, marginTop: 2 },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 12 },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 20 },
  actionBtnText: { color: '#fff', fontWeight: '700', fontSize: 12 },

  empty: { alignItems: 'center', paddingVertical: 40 },
  emptyIcon: { fontSize: 32, marginBottom: 8 },
  emptyText: { color: '#1e1b4b', opacity: 0.4, fontSize: 14 },
});
