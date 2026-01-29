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
import { useFocusEffect } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';

export default function ProgressScreen() {
  const { user } = useAuth();
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [selectedClassroom, setSelectedClassroom] = useState<number | null>(null);
  const [progress, setProgress] = useState<any>(null);
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [dspMetrics, setDspMetrics] = useState<{ students: Array<{ user_id: number; avg_zcr?: number; avg_energy?: number; avg_reading_ratio?: number }> } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [myScores, setMyScores] = useState<any[]>([]);

  const isTeacher = user?.role === 'teacher';

  // Reset state when user changes (e.g., after sign out/sign in with different account)
  useEffect(() => {
    setClassrooms([]);
    setSelectedClassroom(null);
    setProgress(null);
    setDashboardStats(null);
    setDspMetrics(null);
    setMyScores([]);
    setLoading(true);
  }, [user?.id]);

  const loadData = useCallback(async () => {
    if (!user) return; // Don't load if no user
    try {
      const classRes = await api.listClassrooms();
      setClassrooms(classRes);
      if (classRes.length > 0 && !selectedClassroom) {
        setSelectedClassroom(classRes[0].id);
      }
      // Load student's scores
      if (!isTeacher) {
        const assignments = await api.listAssignments();
        console.log('Student assignments:', assignments); // Debug log
        const scores = assignments.filter((a: any) => a.my_score !== null && a.my_score !== undefined);
        console.log('Filtered scores:', scores); // Debug log
        setMyScores(scores);
      }
    } catch (e) {
      console.error('loadData error:', e);
      Alert.alert('Error', 'Could not load data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedClassroom, isTeacher, user]);

  const loadProgress = useCallback(async () => {
    if (!selectedClassroom || !isTeacher) return;
    try {
      const [progressData, stats, dspRes] = await Promise.all([
        api.getClassroomProgress(selectedClassroom),
        api.getTeacherDashboardStats(),
        api.getClassroomDspMetrics(selectedClassroom).catch(() => ({ students: [] })),
      ]);
      setProgress(progressData);
      setDashboardStats(stats);
      setDspMetrics(dspRes);
    } catch (e) {
      console.error(e);
    }
  }, [selectedClassroom, isTeacher]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    loadProgress();
  }, [loadProgress]);

  // Refresh data when screen comes into focus (e.g., after taking a quiz)
  useFocusEffect(
    useCallback(() => {
      if (!loading && user) {
        loadData();
        if (isTeacher) {
          loadProgress();
        }
      }
    }, [loading, user, isTeacher, loadData, loadProgress])
  );

  const onRefresh = () => {
    setRefreshing(true);
    loadData().then(loadProgress).finally(() => setRefreshing(false));
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0a7ea4" />
      </View>
    );
  }

  // Teacher View
  if (isTeacher) {
    const students = progress?.students ?? [];
    const stats = progress?.stats ?? {};

    return (
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Classroom Selector */}
        {classrooms.length > 0 && (
          <View style={styles.filterRow}>
            <Text style={styles.filterLabel}>Classroom:</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
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

        {/* Summary Stats Card */}
        {progress && (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryTitle}>{progress.classroom?.name || 'Classroom'}</Text>
            <View style={styles.summaryRow}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{stats.students_count || 0}</Text>
                <Text style={styles.summaryLabel}>Students</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{stats.average_quiz_score || 0}%</Text>
                <Text style={styles.summaryLabel}>Avg Quiz</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValue}>{stats.average_engagement || 0}</Text>
                <Text style={styles.summaryLabel}>Avg Engagement</Text>
              </View>
            </View>
            <View style={styles.summaryRow}>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValueSmall}>{stats.total_submissions || 0}</Text>
                <Text style={styles.summaryLabel}>Submissions</Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={styles.summaryValueSmall}>{stats.total_sessions || 0}</Text>
                <Text style={styles.summaryLabel}>Study Sessions</Text>
              </View>
            </View>
          </View>
        )}

        {/* Overall Dashboard Stats */}
        {dashboardStats && (
          <View style={styles.overallCard}>
            <Text style={styles.overallTitle}>Overall (All Classrooms)</Text>
            <Text style={styles.overallStat}>
              {dashboardStats.classrooms_count} classrooms | {dashboardStats.materials_count} materials
            </Text>
            <Text style={styles.overallStat}>
              Avg Quiz: {dashboardStats.average_quiz_score}% | Avg Engagement: {dashboardStats.average_engagement_score}
            </Text>
          </View>
        )}

        {/* Student List */}
        <Text style={styles.sectionTitle}>Students</Text>
        {students.length === 0 ? (
          <Text style={styles.empty}>No students enrolled yet. Share your classroom code!</Text>
        ) : (
          students.map((s: any) => (
            <View key={s.user_id} style={styles.card}>
              <Text style={styles.cardTitle}>{s.full_name}</Text>
              <Text style={styles.cardEmail}>{s.email}</Text>
              <View style={styles.statsGrid}>
                <View style={styles.statBox}>
                  <Text style={styles.statValue}>{s.average_score}%</Text>
                  <Text style={styles.statLabel}>Quiz Avg</Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statValue}>{s.average_engagement || 0}</Text>
                  <Text style={styles.statLabel}>Engagement</Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statValue}>{s.submissions_count}</Text>
                  <Text style={styles.statLabel}>Quizzes</Text>
                </View>
                <View style={styles.statBox}>
                  <Text style={styles.statValue}>{s.sessions_count || 0}</Text>
                  <Text style={styles.statLabel}>Sessions</Text>
                </View>
              </View>
              {/* Simple engagement indicator bar */}
              <View style={styles.engagementBar}>
                <View
                  style={[
                    styles.engagementFill,
                    { width: `${Math.min(100, s.average_engagement || 0)}%` },
                  ]}
                />
              </View>
              {/* DSP metrics (ECE): ZCR, Energy, Reading ratio */}
              {dspMetrics?.students?.find((d) => d.user_id === s.user_id) && (() => {
                const dsp = dspMetrics.students.find((d) => d.user_id === s.user_id);
                if (!dsp || (dsp.avg_zcr == null && dsp.avg_energy == null && dsp.avg_reading_ratio == null)) return null;
                return (
                  <Text style={styles.dspRow}>
                    ZCR: {dsp.avg_zcr != null ? dsp.avg_zcr.toFixed(2) : '–'} · Energy: {dsp.avg_energy != null ? dsp.avg_energy : '–'} · Reading: {dsp.avg_reading_ratio != null ? (dsp.avg_reading_ratio * 100).toFixed(1) + '%' : '–'}
                  </Text>
                );
              })()}
            </View>
          ))
        )}
      </ScrollView>
    );
  }

  // Student View
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.sectionTitle}>My Quiz Scores</Text>
      {myScores.length === 0 ? (
        <Text style={styles.empty}>No quiz scores yet. Complete assignments to see your scores.</Text>
      ) : (
        myScores.map((a) => (
          <View key={a.id} style={styles.card}>
            <Text style={styles.cardTitle}>{a.title}</Text>
            <Text style={styles.scoreText}>{a.my_score}%</Text>
          </View>
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
  filterChipActive: { backgroundColor: '#0a7ea4' },
  filterChipText: { fontSize: 14, color: '#333' },
  filterChipTextActive: { color: '#fff' },
  empty: { textAlign: 'center', color: '#666', marginTop: 20, paddingHorizontal: 24 },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 12, marginTop: 16, color: '#333' },

  // Summary Card (Classroom Stats)
  summaryCard: {
    backgroundColor: '#0a7ea4',
    padding: 20,
    borderRadius: 16,
    marginBottom: 16,
  },
  summaryTitle: { fontSize: 20, fontWeight: '700', color: '#fff', marginBottom: 16, textAlign: 'center' },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 12 },
  summaryItem: { alignItems: 'center' },
  summaryValue: { fontSize: 28, fontWeight: '700', color: '#fff' },
  summaryValueSmall: { fontSize: 20, fontWeight: '600', color: '#fff' },
  summaryLabel: { fontSize: 12, color: 'rgba(255,255,255,0.8)', marginTop: 2 },

  // Overall Dashboard Stats
  overallCard: {
    backgroundColor: '#f0f0f0',
    padding: 12,
    borderRadius: 10,
    marginBottom: 16,
  },
  overallTitle: { fontSize: 14, fontWeight: '600', color: '#666', marginBottom: 4 },
  overallStat: { fontSize: 13, color: '#666' },

  // Student Card
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
  cardTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 2 },
  cardEmail: { fontSize: 13, color: '#666', marginBottom: 12 },
  statsGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statBox: { alignItems: 'center', flex: 1 },
  statValue: { fontSize: 18, fontWeight: '700', color: '#0a7ea4' },
  statLabel: { fontSize: 11, color: '#666', marginTop: 2 },

  // Engagement Bar
  engagementBar: {
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    overflow: 'hidden',
  },
  engagementFill: {
    height: '100%',
    backgroundColor: '#0a7ea4',
    borderRadius: 3,
  },
  dspRow: { fontSize: 11, color: '#888', marginTop: 8 },

  scoreText: { fontSize: 24, color: '#0a7ea4', fontWeight: '700' },
});
