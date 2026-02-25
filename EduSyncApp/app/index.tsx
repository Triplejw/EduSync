import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import Constants from 'expo-constants';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import { getAuthErrorMessage } from '@/lib/authErrors';
import { checkBackendHealth } from '@/lib/api';
import { API_URL } from '@/lib/config';

// Show debug UI only in development mode or when explicitly enabled
const SHOW_DEBUG_UI = __DEV__ || process.env.EXPO_PUBLIC_DEBUG === '1';

export default function LoginScreen() {
  const router = useRouter();
  const { user, loading, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      const ok = await checkBackendHealth();
      if (ok) {
        Alert.alert('Success', `Backend is reachable at ${API_URL}`);
      } else {
        Alert.alert('Error', `Backend unreachable at ${API_URL}\n\nMake sure:\n1. Backend is running (uvicorn main:app --host 0.0.0.0)\n2. IP in lib/config.ts is correct`);
      }
    } catch (e) {
      Alert.alert('Error', `Connection failed to ${API_URL}`);
    } finally {
      setTesting(false);
    }
  };

  // Quick login for debugging
  const quickLogin = async (testEmail: string) => {
    setSubmitting(true);
    try {
      await login(testEmail, 'test123');
      router.replace('/(tabs)');
    } catch (e: unknown) {
      Alert.alert('Error', getAuthErrorMessage(e, 'Quick login failed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please enter email and password');
      return;
    }
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace('/(tabs)');
    } catch (e: unknown) {
      Alert.alert('Error', getAuthErrorMessage(e, 'Login failed'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#00BCD4" />
      </View>
    );
  }

  // If already logged in, show continue button (e.g., on app launch with persisted auth)
  if (user) {
    return (
      <View style={styles.container}>
        <View style={styles.inner}>
          <View style={styles.header}>
            <Image source={require('@/assets/images/icon.png')} style={styles.headerIcon} contentFit="contain" />
            <Text style={styles.title}>EduSync</Text>
            <Text style={styles.subtitle}>Welcome back, {user.full_name || user.email}!</Text>
          </View>
          <TouchableOpacity style={styles.btn} onPress={() => router.replace('/(tabs)')}>
            <Text style={styles.btnText}>Continue to App</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.inner}>
        <View style={styles.header}>
          <Image source={require('@/assets/images/splash-icon.png')} style={styles.heroIcon} contentFit="contain" />
          <Text style={styles.title}>EduSync</Text>
          <Text style={styles.subtitle}>Edge AI-Powered Learning Platform</Text>
          <Text style={styles.tagline}>Edge AI Analytics | On-Device Inference | Low Latency</Text>
        </View>

        <View style={styles.form}>
          <TextInput
            placeholder="Email"
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholderTextColor="#999"
          />
          <TextInput
            placeholder="Password"
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholderTextColor="#999"
          />

          <TouchableOpacity
            style={[styles.btn, submitting && styles.btnDisabled]}
            onPress={handleLogin}
            disabled={submitting}
          >
            <Text style={styles.btnText}>{submitting ? 'Signing in...' : 'Sign In'}</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.push('/register')} style={styles.link}>
            <Text style={styles.linkText}>New here? Create Account</Text>
          </TouchableOpacity>
        </View>

        {/* Quick Login Buttons - Only shown in development */}
        {SHOW_DEBUG_UI && (
          <View style={styles.quickLogin}>
            <Text style={styles.quickLoginLabel}>Quick Login (Debug Mode)</Text>
            <View style={styles.quickLoginRow}>
              <TouchableOpacity
                style={styles.quickBtn}
                onPress={() => quickLogin('teacher@test.com')}
                disabled={submitting}
              >
                <Text style={styles.quickBtnText}>Teacher</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.quickBtn}
                onPress={() => quickLogin('student@test.com')}
                disabled={submitting}
              >
                <Text style={styles.quickBtnText}>Student</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Connection test - Only shown in development */}
        {SHOW_DEBUG_UI && (
          <View style={styles.footer}>
            <TouchableOpacity
              onPress={handleTestConnection}
              style={styles.testBtn}
              disabled={testing}
            >
              <Text style={styles.testBtnText}>
                {testing ? 'Testing...' : 'Test Connection'}
              </Text>
            </TouchableOpacity>
            <Text style={styles.serverInfo}>{API_URL}</Text>
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f8fafc' },
  inner: { flex: 1, justifyContent: 'center', padding: 24 },
  header: { alignItems: 'center', marginBottom: 32 },
  headerIcon: { width: 64, height: 64, marginBottom: 12 },
  heroIcon: { width: 100, height: 100, marginBottom: 16 },
  title: { fontSize: 42, fontWeight: 'bold', color: '#00BCD4', textAlign: 'center' },
  subtitle: { fontSize: 18, color: '#333', textAlign: 'center', marginTop: 8, fontWeight: '500' },
  tagline: { fontSize: 12, color: '#666', textAlign: 'center', marginTop: 8, letterSpacing: 0.5 },
  form: { marginBottom: 24 },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 16,
    borderRadius: 12,
    fontSize: 16,
    color: '#333',
  },
  btn: {
    backgroundColor: '#00BCD4',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#00BCD4',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  link: { marginTop: 20, alignItems: 'center' },
  linkText: { color: '#00BCD4', fontSize: 16 },
  quickLogin: { 
    backgroundColor: '#e8f4f8', 
    padding: 16, 
    borderRadius: 12, 
    marginBottom: 24,
  },
  quickLoginLabel: { 
    fontSize: 12, 
    color: '#666', 
    textAlign: 'center', 
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  quickLoginRow: { flexDirection: 'row', justifyContent: 'center', gap: 12 },
  quickBtn: {
    backgroundColor: '#00BCD4',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  quickBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  footer: { alignItems: 'center' },
  testBtn: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
    alignItems: 'center',
    minWidth: 150,
  },
  testBtnText: { color: '#666', fontSize: 14 },
  serverInfo: { marginTop: 8, textAlign: 'center', color: '#999', fontSize: 11 },
});
