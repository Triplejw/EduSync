import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { useRouter } from 'expo-router';

export default function SignupScreen() {
  const router = useRouter();
  const [role, setRole] = useState<'student' | 'teacher'>('student');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSignup = () => {
    if (!name || !email || !password) {
      Alert.alert("Missing Fields", "Please fill in all fields.");
      return;
    }
    // TODO: Connect to Python Backend (Register API)
    console.log(`Registering ${role}:`, name, email);
    router.replace('/(tabs)/feed');
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Join EduSync</Text>
        <Text style={styles.subtitle}>Create your {role} account</Text>
      </View>

      {/* Role Toggle */}
      <View style={styles.toggleContainer}>
        <TouchableOpacity style={[styles.toggleBtn, role === 'student' && styles.toggleActive]} onPress={() => setRole('student')}>
          <Text style={[styles.toggleText, role === 'student' && styles.activeText]}>Student</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.toggleBtn, role === 'teacher' && styles.toggleActive]} onPress={() => setRole('teacher')}>
          <Text style={[styles.toggleText, role === 'teacher' && styles.activeText]}>Teacher</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>Full Name</Text>
        <TextInput style={styles.input} placeholder="John Doe" value={name} onChangeText={setName} />

        <Text style={styles.label}>Email</Text>
        <TextInput style={styles.input} placeholder="id@university.edu" value={email} onChangeText={setEmail} autoCapitalize="none" />

        <Text style={styles.label}>Password</Text>
        <TextInput style={styles.input} placeholder="••••••••" secureTextEntry value={password} onChangeText={setPassword} />

        <TouchableOpacity style={styles.signupBtn} onPress={handleSignup}>
          <Text style={styles.btnText}>Create Account</Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => router.back()} style={styles.loginLink}>
          <Text style={styles.linkText}>Already have an account? <Text style={{fontWeight: 'bold'}}>Log In</Text></Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 24, justifyContent: 'center' },
  header: { marginBottom: 32 },
  title: { fontSize: 32, fontWeight: '700', color: '#111' },
  subtitle: { fontSize: 16, color: '#666', marginTop: 4 },
  toggleContainer: { flexDirection: 'row', backgroundColor: '#f0f0f0', borderRadius: 12, padding: 4, marginBottom: 24 },
  toggleBtn: { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: 10 },
  toggleActive: { backgroundColor: '#fff', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  toggleText: { fontWeight: '600', color: '#666' },
  activeText: { color: '#007AFF' },
  form: { gap: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: -8 },
  input: { backgroundColor: '#f9f9f9', borderWidth: 1, borderColor: '#eee', borderRadius: 12, padding: 16, fontSize: 16 },
  signupBtn: { backgroundColor: '#007AFF', borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 8 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  loginLink: { alignItems: 'center', marginTop: 16 },
  linkText: { color: '#007AFF' },
});
