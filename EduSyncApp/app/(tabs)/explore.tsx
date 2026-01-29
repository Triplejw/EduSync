import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';

export default function ClassroomsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [newName, setNewName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const data = await api.listClassrooms();
      setClassrooms(data);
    } catch (e) {
      console.error(e);
      Alert.alert('Error', 'Could not load classrooms');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      Alert.alert('Error', 'Enter classroom name');
      return;
    }
    setSubmitting(true);
    try {
      const data = await api.createClassroom(newName.trim());
      Alert.alert('Success', `Classroom created! Share code: ${data.code}`);
      setNewName('');
      setShowCreate(false);
      loadData();
    } catch (e) {
      Alert.alert('Error', 'Could not create classroom');
    } finally {
      setSubmitting(false);
    }
  };

  const handleJoin = async () => {
    if (!joinCode.trim()) {
      Alert.alert('Error', 'Enter classroom code');
      return;
    }
    setSubmitting(true);
    try {
      const data = await api.joinClassroom(joinCode.trim().toUpperCase());
      Alert.alert('Success', `Joined ${data.name}!`);
      setJoinCode('');
      setShowJoin(false);
      loadData();
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Could not join'
        : 'Could not join';
      Alert.alert('Error', String(msg));
    } finally {
      setSubmitting(false);
    }
  };

  const isTeacher = user?.role === 'teacher';
  const { logout } = useAuth();

  const handleSignOut = () => {
    // Navigate first, then logout
    router.replace('/');
    setTimeout(() => logout(), 50);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0a7ea4" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {isTeacher ? (
        <TouchableOpacity style={styles.btn} onPress={() => setShowCreate(true)}>
          <Text style={styles.btnText}>➕ Create Classroom</Text>
        </TouchableOpacity>
      ) : (
        <TouchableOpacity style={styles.btn} onPress={() => setShowJoin(true)}>
          <Text style={styles.btnText}>🔗 Join Classroom</Text>
        </TouchableOpacity>
      )}

      {showCreate && (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Classroom name"
            value={newName}
            onChangeText={setNewName}
          />
          <View style={styles.formRow}>
            <TouchableOpacity style={styles.formBtn} onPress={handleCreate} disabled={submitting}>
              <Text style={styles.formBtnText}>{submitting ? 'Creating...' : 'Create'}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.formBtn, styles.formBtnCancel]} onPress={() => setShowCreate(false)}>
              <Text style={styles.formBtnText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {showJoin && (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Classroom code (e.g. ABC123)"
            value={joinCode}
            onChangeText={setJoinCode}
            autoCapitalize="characters"
          />
          <View style={styles.formRow}>
            <TouchableOpacity style={styles.formBtn} onPress={handleJoin} disabled={submitting}>
              <Text style={styles.formBtnText}>{submitting ? 'Joining...' : 'Join'}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.formBtn, styles.formBtnCancel]} onPress={() => setShowJoin(false)}>
              <Text style={styles.formBtnText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      <Text style={styles.sectionTitle}>My Classrooms</Text>
      {classrooms.length === 0 ? (
        <Text style={styles.empty}>
          {isTeacher ? 'Create a classroom to get started.' : 'Join a classroom with a code from your teacher.'}
        </Text>
      ) : (
        classrooms.map((c) => (
          <View key={c.id} style={styles.card}>
            <Text style={styles.cardTitle}>{c.name}</Text>
            {isTeacher && <Text style={styles.cardCode}>Code: {c.code}</Text>}
          </View>
        ))
      )}

      <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
        <Text style={styles.signOutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  btn: {
    backgroundColor: '#0a7ea4',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 20,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  form: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 20 },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 14,
    borderRadius: 10,
    marginBottom: 12,
    fontSize: 16,
  },
  formRow: { flexDirection: 'row', gap: 12 },
  formBtn: {
    flex: 1,
    backgroundColor: '#0a7ea4',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  formBtnCancel: { backgroundColor: '#999' },
  formBtnText: { color: '#fff', fontWeight: '600' },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 12, color: '#333' },
  empty: { textAlign: 'center', color: '#666', marginTop: 20, paddingHorizontal: 24 },
  card: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  cardTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 4 },
  cardCode: { fontSize: 14, color: '#666', fontFamily: 'monospace' },
  signOutBtn: {
    marginTop: 32,
    padding: 16,
    alignItems: 'center',
    borderTopWidth: 1,
    borderColor: '#eee',
  },
  signOutText: { color: '#d9534f', fontSize: 16, fontWeight: '600' },
});
