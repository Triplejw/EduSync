import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Image, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';

export default function LoginScreen() {
  const router = useRouter();
  const [isTeacher, setIsTeacher] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    console.log("Logging in as:", isTeacher ? "Teacher" : "Student");
    // Now this will work because we disabled the "Guard" in _layout.tsx
    router.replace('/(tabs)/feed');
  };

  return (
    <KeyboardAvoidingView 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.logoContainer}>
        {/* UPDATED: Using your App Icon */}
        <Image 
          source={require('../../assets/images/icon.png')} 
          style={styles.logoImage} 
          resizeMode="contain"
        />
        <Text style={styles.appName}>EduSync</Text>
        <Text style={styles.tagline}>Intelligent Edge Learning</Text>
      </View>

      <View style={styles.formContainer}>
        {/* Role Toggle */}
        <View style={styles.toggleContainer}>
          <TouchableOpacity 
            style={[styles.toggleBtn, !isTeacher && styles.toggleActive]} 
            onPress={() => setIsTeacher(false)}
          >
            <Text style={[styles.toggleText, !isTeacher && styles.activeText]}>Student</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.toggleBtn, isTeacher && styles.toggleActive]} 
            onPress={() => setIsTeacher(true)}
          >
            <Text style={[styles.toggleText, isTeacher && styles.activeText]}>Teacher</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.label}>Institutional Email</Text>
        <TextInput 
          style={styles.input} 
          placeholder="id@university.edu" 
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
        />

        <Text style={styles.label}>Password</Text>
        <TextInput 
          style={styles.input} 
          placeholder="••••••••" 
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
          <Text style={styles.loginButtonText}>Sign In</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.linkContainer} 
          onPress={() => router.push('/(auth)/signup')}
        >
          <Text style={styles.linkText}>Don't have an account? <Text style={{fontWeight: 'bold'}}>Sign Up</Text></Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF', padding: 20, justifyContent: 'center' },
  logoContainer: { alignItems: 'center', marginBottom: 40 },
  
  // NEW STYLE FOR ICON
  logoImage: { width: 100, height: 100, marginBottom: 15 },
  
  appName: { fontSize: 32, fontWeight: 'bold', color: '#1c1c1e' },
  tagline: { fontSize: 16, color: '#8e8e93', marginTop: 5 },
  formContainer: { width: '100%' },
  toggleContainer: { flexDirection: 'row', backgroundColor: '#F2F2F7', borderRadius: 12, padding: 4, marginBottom: 25 },
  toggleBtn: { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: 10 },
  toggleActive: { backgroundColor: '#FFFFFF', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  toggleText: { fontWeight: '600', color: '#8e8e93' },
  activeText: { color: '#007AFF' },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 8, marginLeft: 4 },
  input: { backgroundColor: '#F2F2F7', borderRadius: 12, padding: 16, fontSize: 16, marginBottom: 20 },
  loginButton: { backgroundColor: '#007AFF', borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginTop: 10 },
  loginButtonText: { color: '#FFFFFF', fontSize: 18, fontWeight: 'bold' },
  linkContainer: { alignItems: 'center', marginTop: 20 },
  linkText: { color: '#007AFF', fontSize: 14, fontWeight: '500' },
});
