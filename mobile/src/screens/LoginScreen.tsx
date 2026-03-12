import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform,
  ActivityIndicator, Alert, ScrollView,
} from 'react-native';
import { useAuth } from '../hooks/useAuth';

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Missing fields', 'Please enter your email and password.');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
    } catch {
      Alert.alert('Login failed', 'Incorrect email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">

        {/* Brand header */}
        <View style={styles.header}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoText}>SPT</Text>
          </View>
          <Text style={styles.orgName}>Arkwright Engineering Scholars</Text>
          <Text style={styles.appName}>Mentoring Platform</Text>
        </View>

        {/* Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Sign in</Text>
          <Text style={styles.cardSubtitle}>Welcome back — please sign in to continue.</Text>

          <Text style={styles.label}>Email address</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            placeholderTextColor="#94a3b8"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            placeholderTextColor="#94a3b8"
            secureTextEntry
            autoComplete="current-password"
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.buttonText}>Sign in</Text>}
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>
          Need access? Contact your SPT coordinator.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: '#f8f7fc' },
  container: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },

  header: { alignItems: 'center', marginBottom: 32 },
  logoCircle: {
    width: 64, height: 64, borderRadius: 20,
    backgroundColor: '#9333ea', alignItems: 'center', justifyContent: 'center',
    marginBottom: 12, shadowColor: '#9333ea', shadowOpacity: 0.4, shadowRadius: 12, elevation: 6,
  },
  logoText: { color: '#fff', fontWeight: '800', fontSize: 18 },
  orgName: { color: '#ec4899', fontWeight: '700', fontSize: 13, letterSpacing: 0.5 },
  appName: { color: '#1e1b4b', opacity: 0.5, fontSize: 12, marginTop: 2 },

  card: {
    width: '100%', maxWidth: 380, backgroundColor: '#fff',
    borderRadius: 20, padding: 24,
    shadowColor: '#9333ea', shadowOpacity: 0.08, shadowRadius: 16, elevation: 4,
  },
  cardTitle: { fontSize: 22, fontWeight: '800', color: '#1e1b4b', marginBottom: 4 },
  cardSubtitle: { fontSize: 13, color: '#1e1b4b', opacity: 0.5, marginBottom: 24 },

  label: { fontSize: 12, fontWeight: '600', color: '#1e1b4b', marginBottom: 6 },
  input: {
    borderWidth: 1, borderColor: '#e8e3f5', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 14, color: '#1e1b4b', marginBottom: 16, backgroundColor: '#fafafa',
  },

  button: {
    backgroundColor: '#9333ea', borderRadius: 14,
    paddingVertical: 14, alignItems: 'center', marginTop: 8,
    shadowColor: '#9333ea', shadowOpacity: 0.3, shadowRadius: 8, elevation: 4,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 15 },

  footer: { marginTop: 24, fontSize: 12, color: '#1e1b4b', opacity: 0.4, textAlign: 'center' },
});
