import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Alert, ActivityIndicator,
} from 'react-native';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../hooks/useAuth';
import api from '../hooks/api';

const ROLE_COLORS: Record<string, string> = {
  scholar: '#9333ea',
  mentor: '#1e40af',
  sponsor: '#f59e0b',
  alumni: '#ec4899',
  admin: '#6b7280',
};

export default function ProfileScreen() {
  const { user, logout, fetchCurrentUser } = useAuth();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState(user?.bio ?? '');
  const [location, setLocation] = useState(user?.location ?? '');

  const save = useMutation({
    mutationFn: () => api.patch(`/users/${user?.id}/`, { bio, location }),
    onSuccess: async () => {
      await fetchCurrentUser();
      setEditing(false);
    },
    onError: () => Alert.alert('Error', 'Failed to save changes.'),
  });

  const handleLogout = () => {
    Alert.alert('Sign out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign out', style: 'destructive', onPress: logout },
    ]);
  };

  if (!user) return <ActivityIndicator color="#9333ea" style={{ flex: 1 }} />;

  const initials = `${user.first_name[0]}${user.last_name[0]}`;
  const roleColor = ROLE_COLORS[user.role] ?? '#6b7280';

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>

      {/* Profile header */}
      <View style={styles.header}>
        <View style={[styles.avatarLarge, { shadowColor: roleColor }]}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.fullName}>{user.full_name}</Text>
        <View style={[styles.roleBadge, { backgroundColor: roleColor + '20' }]}>
          <Text style={[styles.roleText, { color: roleColor }]}>{user.role}</Text>
        </View>
        {user.is_verified && (
          <View style={styles.verifiedBadge}>
            <Ionicons name="checkmark-circle" size={14} color="#22c55e" />
            <Text style={styles.verifiedText}>Safeguarding verified</Text>
          </View>
        )}
      </View>

      {/* Info card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Personal information</Text>

        <View style={styles.row}>
          <Ionicons name="mail-outline" size={16} color="#9333ea" />
          <Text style={styles.rowText}>{user.email}</Text>
        </View>

        {user.engineering_discipline && (
          <View style={styles.row}>
            <Ionicons name="construct-outline" size={16} color="#9333ea" />
            <Text style={styles.rowText}>{user.engineering_discipline}</Text>
          </View>
        )}

        {editing ? (
          <>
            <Text style={styles.label}>Location</Text>
            <TextInput
              style={styles.input}
              value={location}
              onChangeText={setLocation}
              placeholder="e.g. London, UK"
              placeholderTextColor="#94a3b8"
            />
            <Text style={styles.label}>Bio</Text>
            <TextInput
              style={[styles.input, { height: 90, textAlignVertical: 'top' }]}
              value={bio}
              onChangeText={setBio}
              placeholder="Tell us about yourself..."
              placeholderTextColor="#94a3b8"
              multiline
            />
            <View style={styles.editActions}>
              <TouchableOpacity
                style={styles.saveBtn}
                onPress={() => save.mutate()}
                disabled={save.isPending}
              >
                {save.isPending
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.saveBtnText}>Save changes</Text>}
              </TouchableOpacity>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setEditing(false)}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </>
        ) : (
          <>
            {user.location ? (
              <View style={styles.row}>
                <Ionicons name="location-outline" size={16} color="#9333ea" />
                <Text style={styles.rowText}>{user.location}</Text>
              </View>
            ) : null}
            {user.bio ? (
              <Text style={styles.bio}>{user.bio}</Text>
            ) : null}
            <TouchableOpacity style={styles.editBtn} onPress={() => setEditing(true)}>
              <Ionicons name="pencil-outline" size={14} color="#9333ea" />
              <Text style={styles.editBtnText}>Edit profile</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      {/* Sign out */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={18} color="#ef4444" />
        <Text style={styles.logoutText}>Sign out</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f7fc' },

  header: { alignItems: 'center', paddingTop: 32, paddingBottom: 24, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f3e8ff' },
  avatarLarge: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: '#9333ea', alignItems: 'center', justifyContent: 'center',
    shadowOpacity: 0.3, shadowRadius: 12, elevation: 6, marginBottom: 12,
  },
  avatarText: { color: '#fff', fontWeight: '800', fontSize: 28 },
  fullName: { fontSize: 20, fontWeight: '800', color: '#1e1b4b', marginBottom: 6 },
  roleBadge: { paddingHorizontal: 12, paddingVertical: 4, borderRadius: 20, marginBottom: 8 },
  roleText: { fontSize: 12, fontWeight: '700', textTransform: 'capitalize' },
  verifiedBadge: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  verifiedText: { fontSize: 12, color: '#22c55e', fontWeight: '600' },

  card: {
    backgroundColor: '#fff', margin: 16, borderRadius: 16, padding: 16,
    shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2,
  },
  cardTitle: { fontSize: 14, fontWeight: '700', color: '#1e1b4b', marginBottom: 14 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  rowText: { fontSize: 14, color: '#1e1b4b', flex: 1 },
  bio: { fontSize: 13, color: '#1e1b4b', opacity: 0.7, lineHeight: 20, marginBottom: 12 },

  label: { fontSize: 12, fontWeight: '600', color: '#1e1b4b', marginBottom: 6, marginTop: 4 },
  input: {
    borderWidth: 1, borderColor: '#e8e3f5', borderRadius: 10, padding: 10,
    fontSize: 13, color: '#1e1b4b', backgroundColor: '#fafafa', marginBottom: 12,
  },
  editActions: { flexDirection: 'row', gap: 10 },
  saveBtn: { flex: 1, backgroundColor: '#9333ea', borderRadius: 12, paddingVertical: 12, alignItems: 'center' },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  cancelBtn: { flex: 1, borderWidth: 1, borderColor: '#e8e3f5', borderRadius: 12, paddingVertical: 12, alignItems: 'center' },
  cancelBtnText: { color: '#1e1b4b', fontSize: 13, opacity: 0.6 },

  editBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8 },
  editBtnText: { color: '#9333ea', fontWeight: '600', fontSize: 13 },

  logoutBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    marginHorizontal: 16, backgroundColor: '#fff', borderRadius: 14, padding: 16,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  logoutText: { color: '#ef4444', fontWeight: '700', fontSize: 15 },
});
