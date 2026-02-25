import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';

export default function AssignmentsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [assignments, setAssignments] = useState<any[]>([]);
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedClassroom, setSelectedClassroom] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [assignRes, classRes] = await Promise.all([
        api.listAssignments(selectedClassroom ?? undefined),
        api.listClassrooms(),
      ]);
      setAssignments(assignRes);
      setClassrooms(classRes);
    } catch (e) {
      console.error(e);
      Alert.alert('Error', 'Could not load assignments');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedClassroom]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const isTeacher = user?.role === 'teacher';

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
      {classrooms.length > 0 && (
        <View style={styles.filterRow}>
          <Text style={styles.filterLabel}>Classroom:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <TouchableOpacity
              style={[styles.filterChip, !selectedClassroom && styles.filterChipActive]}
              onPress={() => setSelectedClassroom(null)}
            >
              <Text style={[styles.filterChipText, !selectedClassroom && styles.filterChipTextActive]}>All</Text>
            </TouchableOpacity>
            {classrooms.map((c) => (
              <TouchableOpacity
                key={c.id}
                style={[styles.filterChip, selectedClassroom === c.id && styles.filterChipActive]}
                onPress={() => setSelectedClassroom(c.id)}
              >
                <Text style={[styles.filterChipText, selectedClassroom === c.id && styles.filterChipTextActive]}>
                  {c.name}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {assignments.length === 0 ? (
        <Text style={styles.empty}>
          {isTeacher ? 'No assignments yet. Create one from a material.' : 'No assignments yet.'}
        </Text>
      ) : (
        assignments.map((a) => (
          <TouchableOpacity
            key={a.id}
            style={styles.card}
            onPress={() => router.push(`/assignment/${a.id}`)}
          >
            <Text style={styles.cardTitle}>{a.title}</Text>
            <View style={styles.cardMeta}>
              {isTeacher && (
                <Text style={styles.metaText}>{a.submission_count} submission(s)</Text>
              )}
              {a.my_score != null && (
                <Text style={styles.scoreText}>Your score: {a.my_score}%</Text>
              )}
            </View>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  filterRow: { marginBottom: 16 },
  filterLabel: { fontSize: 14, color: '#666', marginBottom: 8 },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#e0e0e0',
    marginRight: 8,
  },
  filterChipActive: { backgroundColor: '#00BCD4' },
  filterChipText: { fontSize: 14, color: '#333' },
  filterChipTextActive: { color: '#fff' },
  empty: { textAlign: 'center', color: '#666', marginTop: 40, paddingHorizontal: 24 },
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
  cardTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 6 },
  cardMeta: { flexDirection: 'row', gap: 12 },
  metaText: { fontSize: 14, color: '#666' },
  scoreText: { fontSize: 14, color: '#00BCD4', fontWeight: '600' },
});
