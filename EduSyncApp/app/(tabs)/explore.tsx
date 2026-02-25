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
import { useIntro } from '@/context/IntroContext';
import * as api from '@/lib/api';

export default function ClassroomsScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { triggerIntro } = useIntro();
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSubject, setNewSubject] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isTeacher = user?.role === 'teacher';

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
      const data = await api.createClassroom(newName.trim(), newSubject.trim() || undefined);
      Alert.alert('Success', `Classroom created!\nShare code: ${data.code}`);
      setNewName('');
      setNewSubject('');
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

  const doLogout = () => {
    // Show intro animation first, then clear auth after a brief delay
    // so the intro overlay mounts before auth state clears.
    triggerIntro();
    setTimeout(() => {
      logout();
    }, 100);
  };

  const handleLogOut = () => {
    Alert.alert('Log out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: doLogout },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#00BCD4" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Create/Join button */}
      {isTeacher ? (
        <TouchableOpacity style={styles.btn} onPress={() => setShowCreate(true)}>
          <Text style={styles.btnText}>+ Create Classroom</Text>
        </TouchableOpacity>
      ) : (
        <TouchableOpacity style={styles.btn} onPress={() => setShowJoin(true)}>
          <Text style={styles.btnText}>+ Join Classroom</Text>
        </TouchableOpacity>
      )}

      {/* Create form */}
      {showCreate && (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Classroom name (e.g. Math 101)"
            value={newName}
            onChangeText={setNewName}
            placeholderTextColor="#999"
          />
          <TextInput
            style={styles.input}
            placeholder="Subject (e.g. Mathematics) - optional"
            value={newSubject}
            onChangeText={setNewSubject}
            placeholderTextColor="#999"
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

      {/* Join form */}
      {showJoin && (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Classroom code (e.g. ABC123)"
            value={joinCode}
            onChangeText={setJoinCode}
            autoCapitalize="characters"
            placeholderTextColor="#999"
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

      {/* Classrooms list */}
      <Text style={styles.sectionTitle}>My Classrooms</Text>
      {classrooms.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>{isTeacher ? '📚' : '🎓'}</Text>
          <Text style={styles.empty}>
            {isTeacher
              ? 'Create your first classroom to start teaching.'
              : 'Join a classroom with a code from your teacher.'}
          </Text>
        </View>
      ) : (
        classrooms.map((c) => (
          <TouchableOpacity
            key={c.id}
            style={styles.card}
            onPress={() => router.push(`/classroom/${c.id}`)}
            activeOpacity={0.7}
          >
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{c.name}</Text>
              {c.subject_name && <Text style={styles.cardSubject}>{c.subject_name}</Text>}
            </View>
            <View style={styles.cardMeta}>
              {isTeacher ? (
                <Text style={styles.cardCode}>Code: {c.code}</Text>
              ) : (
                <Text style={styles.cardTeacher}>Teacher: {c.teacher_name || 'Unknown'}</Text>
              )}
            </View>
            <Text style={styles.cardHint}>Tap to open →</Text>
          </TouchableOpacity>
        ))
      )}

      {/* Log out */}
      <TouchableOpacity style={styles.logOutBtn} onPress={handleLogOut}>
        <Text style={styles.logOutText}>Log out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  btn: {
    backgroundColor: '#00BCD4',
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
    color: '#333',
  },
  formRow: { flexDirection: 'row', gap: 12 },
  formBtn: {
    flex: 1,
    backgroundColor: '#00BCD4',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  formBtnCancel: { backgroundColor: '#999' },
  formBtnText: { color: '#fff', fontWeight: '600' },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 12, color: '#333' },
  emptyContainer: { alignItems: 'center', paddingVertical: 40 },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  empty: { textAlign: 'center', color: '#666', paddingHorizontal: 24, lineHeight: 22 },
  card: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#00BCD4',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: { marginBottom: 8 },
  cardTitle: { fontSize: 18, fontWeight: '700', color: '#1a1a1a' },
  cardSubject: { fontSize: 14, color: '#00BCD4', marginTop: 4 },
  cardMeta: { marginBottom: 8 },
  cardCode: { fontSize: 14, color: '#666', fontFamily: 'monospace' },
  cardTeacher: { fontSize: 14, color: '#666' },
  cardHint: { fontSize: 12, color: '#aaa', textAlign: 'right' },
  logOutBtn: {
    marginTop: 32,
    padding: 16,
    alignItems: 'center',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
  },
  logOutText: { color: '#666', fontSize: 16, fontWeight: '500' },
});
