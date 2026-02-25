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
  ScrollView,
} from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import { getAuthErrorMessage } from '@/lib/authErrors';

export default function RegisterScreen() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'teacher' | 'student'>('student');
  const [submitting, setSubmitting] = useState(false);

  const handleRegister = async () => {
    if (!email || !password || !fullName) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, fullName, role);
      router.replace('/(tabs)');
    } catch (e: unknown) {
      Alert.alert('Error', getAuthErrorMessage(e, 'Registration failed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.inner}>
        <View style={styles.header}>
          <Image source={require('@/assets/images/icon.png')} style={styles.headerIcon} contentFit="contain" />
          <Text style={styles.title}>Join EduSync</Text>
        </View>

        <TextInput
          placeholder="Full Name"
          style={styles.input}
          value={fullName}
          onChangeText={setFullName}
          placeholderTextColor="#999"
        />
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

        <Text style={styles.label}>I am a:</Text>
        <View style={styles.roleRow}>
          <TouchableOpacity
            style={[styles.roleBtn, role === 'student' && styles.roleSelected]}
            onPress={() => setRole('student')}
          >
            <Text style={[styles.roleText, role === 'student' && styles.roleTextSelected]}>Student</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.roleBtn, role === 'teacher' && styles.roleSelected]}
            onPress={() => setRole('teacher')}
          >
            <Text style={[styles.roleText, role === 'teacher' && styles.roleTextSelected]}>Teacher</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={[styles.btn, submitting && styles.btnDisabled]}
          onPress={handleRegister}
          disabled={submitting}
        >
          <Text style={styles.btnText}>{submitting ? 'Creating...' : 'Create Account'}</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.back()} style={styles.link}>
          <Text style={styles.linkText}>Already have an account? Sign In</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  inner: { flexGrow: 1, padding: 24, paddingTop: 48 },
  header: { alignItems: 'center', marginBottom: 16 },
  headerIcon: { width: 56, height: 56, marginBottom: 12 },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 24, textAlign: 'center', color: '#00BCD4' },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
    padding: 14,
    marginBottom: 16,
    borderRadius: 10,
    fontSize: 16,
    color: '#333',
  },
  label: { fontSize: 16, marginBottom: 10, marginTop: 8 },
  roleRow: { flexDirection: 'row', gap: 12, marginBottom: 24 },
  roleBtn: {
    flex: 1,
    padding: 14,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    alignItems: 'center',
  },
  roleSelected: { backgroundColor: '#00BCD4', borderColor: '#00BCD4' },
  roleText: { fontSize: 16, color: '#333' },
  roleTextSelected: { color: '#fff', fontWeight: '600' },
  btn: {
    backgroundColor: '#00BCD4',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  link: { marginTop: 24, alignItems: 'center' },
  linkText: { color: '#00BCD4', fontSize: 16 },
});
