import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../hooks/useAuth';
import api from '../hooks/api';
import type { MentoringSession, Notification, Goal } from '../types';

function StatCard({ label, value, icon, color }: {
  label: string; value: string | number; icon: string; color: string;
}) {
  return (
    <View style={[styles.statCard, { borderTopColor: color }]}>
      <Text style={{ fontSize: 20 }}>{icon}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function QuickActionButton({ icon, label, onPress, color }: {
  icon: keyof typeof Ionicons.glyphMap; label: string; onPress: () => void; color: string;
}) {
  return (
    <TouchableOpacity style={styles.quickAction} onPress={onPress} activeOpacity={0.8}>
      <View style={[styles.quickActionIcon, { backgroundColor: color + '20' }]}>
        <Ionicons name={icon} size={22} color={color} />
      </View>
      <Text style={styles.quickActionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

export default function HomeScreen() {
  const { user } = useAuth();
  const navigation = useNavigation<any>();

  const { data: sessions = [], isLoading: loadingSessions } = useQuery<MentoringSession[]>({
    queryKey: ['home-sessions'],
    queryFn: () => api.get('/sessions/sessions/?is_upcoming=true').then(r => r.data.results ?? r.data),
  });

  const { data: goals = [] } = useQuery<Goal[]>({
    queryKey: ['home-goals'],
    queryFn: () => api.get('/goals/?status=active').then(r => r.data.results ?? r.data),
  });

  const { data: notifData } = useQuery<{ count: number }>({
    queryKey: ['notif-count'],
    queryFn: () => api.get('/notifications/unread_count/').then(r => r.data),
  });

  const upcomingSessions = sessions.filter(s => s.is_upcoming && s.status === 'confirmed');
  const activeGoals = goals.filter(g => g.status === 'active');

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 32 }}>

      {/* Header */}
      <View style={styles.headerBanner}>
        <Text style={styles.greeting}>{greeting()}, {user?.first_name} 👋</Text>
        <Text style={styles.subGreeting}>Your engineering journey continues</Text>
      </View>

      {/* Stats */}
      <View style={styles.statsRow}>
        <StatCard label="Upcoming" value={upcomingSessions.length} icon="📅" color="#9333ea" />
        <StatCard label="Active Goals" value={activeGoals.length} icon="🎯" color="#ec4899" />
        <StatCard label="Unread" value={notifData?.count ?? 0} icon="🔔" color="#f59e0b" />
      </View>

      {/* Quick actions */}
      <Text style={styles.sectionTitle}>Quick actions</Text>
      <View style={styles.quickActionsGrid}>
        <QuickActionButton icon="calendar" label="Sessions" onPress={() => navigation.navigate('Sessions')} color="#9333ea" />
        <QuickActionButton icon="chatbubbles" label="Messages" onPress={() => navigation.navigate('Messages')} color="#ec4899" />
        <QuickActionButton icon="notifications" label="Notifications" onPress={() => navigation.navigate('Notifications')} color="#f59e0b" />
        <QuickActionButton icon="person" label="Profile" onPress={() => navigation.navigate('Profile')} color="#0ea5e9" />
      </View>

      {/* Upcoming sessions */}
      <Text style={styles.sectionTitle}>Upcoming sessions</Text>
      {loadingSessions ? (
        <ActivityIndicator color="#9333ea" />
      ) : upcomingSessions.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyIcon}>📅</Text>
          <Text style={styles.emptyText}>No upcoming sessions</Text>
        </View>
      ) : (
        upcomingSessions.slice(0, 3).map(s => (
          <View key={s.id} style={styles.sessionCard}>
            <View style={[styles.sessionStatusDot, { backgroundColor: '#22c55e' }]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.sessionTitle}>{s.title}</Text>
              <Text style={styles.sessionMeta}>
                {new Date(s.start_time).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}
                {' · '}
                {new Date(s.start_time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
              </Text>
            </View>
          </View>
        ))
      )}

      {/* Active goals */}
      {activeGoals.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Active goals</Text>
          {activeGoals.slice(0, 2).map(g => (
            <View key={g.id} style={styles.goalCard}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                <Text style={styles.goalTitle}>{g.title}</Text>
                <Text style={styles.goalPercent}>{g.progress_percent}%</Text>
              </View>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${g.progress_percent}%` }]} />
              </View>
            </View>
          ))}
        </>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f7fc' },

  headerBanner: {
    backgroundColor: '#9333ea', paddingHorizontal: 20, paddingTop: 24, paddingBottom: 28,
  },
  greeting: { color: '#fff', fontSize: 22, fontWeight: '800' },
  subGreeting: { color: '#fff', opacity: 0.7, fontSize: 13, marginTop: 4 },

  statsRow: {
    flexDirection: 'row', gap: 10, marginHorizontal: 16, marginTop: -16,
  },
  statCard: {
    flex: 1, backgroundColor: '#fff', borderRadius: 14, padding: 12,
    alignItems: 'center', borderTopWidth: 3,
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 3,
  },
  statValue: { fontSize: 22, fontWeight: '800', color: '#1e1b4b', marginTop: 4 },
  statLabel: { fontSize: 10, color: '#1e1b4b', opacity: 0.5, marginTop: 2, fontWeight: '600' },

  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#1e1b4b', marginHorizontal: 16, marginTop: 24, marginBottom: 10 },

  quickActionsGrid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: 16, gap: 10 },
  quickAction: {
    width: '47%', backgroundColor: '#fff', borderRadius: 14, padding: 16,
    alignItems: 'center', gap: 8,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  quickActionIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  quickActionLabel: { fontSize: 12, fontWeight: '600', color: '#1e1b4b' },

  emptyCard: {
    backgroundColor: '#fff', borderRadius: 14, padding: 24,
    alignItems: 'center', marginHorizontal: 16,
  },
  emptyIcon: { fontSize: 28, marginBottom: 8 },
  emptyText: { color: '#1e1b4b', opacity: 0.4, fontSize: 13 },

  sessionCard: {
    backgroundColor: '#fff', borderRadius: 14, padding: 14,
    flexDirection: 'row', alignItems: 'center', gap: 12,
    marginHorizontal: 16, marginBottom: 8,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  sessionStatusDot: { width: 8, height: 8, borderRadius: 4 },
  sessionTitle: { fontSize: 14, fontWeight: '600', color: '#1e1b4b' },
  sessionMeta: { fontSize: 12, color: '#1e1b4b', opacity: 0.5, marginTop: 2 },

  goalCard: {
    backgroundColor: '#fff', borderRadius: 14, padding: 14,
    marginHorizontal: 16, marginBottom: 8,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  goalTitle: { fontSize: 13, fontWeight: '600', color: '#1e1b4b', flex: 1 },
  goalPercent: { fontSize: 13, fontWeight: '700', color: '#9333ea' },
  progressBar: { height: 6, backgroundColor: '#f3e8ff', borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: '#9333ea', borderRadius: 3 },
});
