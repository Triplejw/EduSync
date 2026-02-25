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
  Dimensions,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';

const { width } = Dimensions.get('window');

// Simple Bar Chart Component (no external dependencies)
function BarChart({ data, maxValue, label }: { data: { name: string; value: number }[]; maxValue: number; label: string }) {
  const barWidth = Math.max(30, (width - 80) / data.length - 8);
  return (
    <View style={chartStyles.container}>
      <Text style={chartStyles.label}>{label}</Text>
      <View style={chartStyles.barsContainer}>
        {data.map((item, i) => {
          const height = maxValue > 0 ? (item.value / maxValue) * 120 : 0;
          return (
            <View key={i} style={[chartStyles.barWrapper, { width: barWidth }]}>
              <Text style={chartStyles.barValue}>{item.value}%</Text>
              <View style={[chartStyles.bar, { height: Math.max(4, height) }]} />
              <Text style={chartStyles.barLabel} numberOfLines={1}>{item.name.split(' ')[0]}</Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

// Pie-like Progress Ring Component
function ProgressRing({ value, maxValue, label, color }: { value: number; maxValue: number; label: string; color: string }) {
  const percentage = maxValue > 0 ? Math.round((value / maxValue) * 100) : 0;
  return (
    <View style={ringStyles.container}>
      <View style={[ringStyles.ring, { borderColor: color }]}>
        <Text style={[ringStyles.value, { color }]}>{percentage}%</Text>
      </View>
      <Text style={ringStyles.label}>{label}</Text>
      <Text style={ringStyles.sublabel}>{value}/{maxValue}</Text>
    </View>
  );
}

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
    if (!user) return;
    try {
      const classRes = await api.listClassrooms();
      setClassrooms(classRes);
      if (classRes.length > 0 && !selectedClassroom) {
        setSelectedClassroom(classRes[0].id);
      }
      if (!isTeacher) {
        const assignments = await api.listAssignments();
        const scores = assignments.filter((a: any) => a.my_score !== null && a.my_score !== undefined);
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
        <ActivityIndicator size="large" color="#00BCD4" />
      </View>
    );
  }

  // Teacher View with Charts
  if (isTeacher) {
    const students = progress?.students ?? [];
    const stats = progress?.stats ?? {};

    // Prepare data for bar chart (student quiz scores)
    const quizScoreData = students.slice(0, 8).map((s: any) => ({
      name: s.full_name || 'Student',
      value: s.average_score || 0,
    }));

    // Calculate submission stats
    const totalPossibleSubmissions = students.length * (stats.assignments_count || 1);
    const actualSubmissions = stats.total_submissions || 0;

    return (
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Classroom Selector */}
        {classrooms.length > 0 && (
          <View style={styles.filterRow}>
            <Text style={styles.filterLabel}>Select Classroom:</Text>
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

        {/* Summary Stats Cards */}
        {progress && (
          <View style={styles.statsCardsRow}>
            <View style={[styles.statsCard, { backgroundColor: '#00BCD4' }]}>
              <Text style={styles.statsCardValue}>{stats.students_count || 0}</Text>
              <Text style={styles.statsCardLabel}>Students</Text>
            </View>
            <View style={[styles.statsCard, { backgroundColor: '#2e7d32' }]}>
              <Text style={styles.statsCardValue}>{stats.average_quiz_score || 0}%</Text>
              <Text style={styles.statsCardLabel}>Avg Score</Text>
            </View>
            <View style={[styles.statsCard, { backgroundColor: '#ed6c02' }]}>
              <Text style={styles.statsCardValue}>{stats.total_submissions || 0}</Text>
              <Text style={styles.statsCardLabel}>Submissions</Text>
            </View>
          </View>
        )}

        {/* Progress Rings */}
        {progress && students.length > 0 && (
          <View style={styles.ringsContainer}>
            <ProgressRing
              value={actualSubmissions}
              maxValue={Math.max(totalPossibleSubmissions, 1)}
              label="Completion"
              color="#2e7d32"
            />
            <ProgressRing
              value={stats.average_engagement || 0}
              maxValue={100}
              label="Engagement"
              color="#00BCD4"
            />
            <ProgressRing
              value={stats.total_sessions || 0}
              maxValue={students.length * 5}
              label="Study Sessions"
              color="#ed6c02"
            />
          </View>
        )}

        {/* Bar Chart: Student Quiz Scores */}
        {quizScoreData.length > 0 && (
          <BarChart data={quizScoreData} maxValue={100} label="Student Quiz Scores" />
        )}

        {/* Overall Dashboard Stats */}
        {dashboardStats && (
          <View style={styles.overallCard}>
            <Text style={styles.overallTitle}>Overall Statistics (All Classrooms)</Text>
            <View style={styles.overallRow}>
              <View style={styles.overallItem}>
                <Text style={styles.overallValue}>{dashboardStats.classrooms_count}</Text>
                <Text style={styles.overallLabel}>Classrooms</Text>
              </View>
              <View style={styles.overallItem}>
                <Text style={styles.overallValue}>{dashboardStats.materials_count}</Text>
                <Text style={styles.overallLabel}>Materials</Text>
              </View>
              <View style={styles.overallItem}>
                <Text style={styles.overallValue}>{dashboardStats.average_quiz_score}%</Text>
                <Text style={styles.overallLabel}>Avg Quiz</Text>
              </View>
            </View>
          </View>
        )}

        {/* Student List */}
        <Text style={styles.sectionTitle}>Student Details</Text>
        {students.length === 0 ? (
          <Text style={styles.empty}>No students enrolled yet. Share your classroom code!</Text>
        ) : (
          students.map((s: any) => {
            const dsp = dspMetrics?.students?.find((d) => d.user_id === s.user_id);
            return (
              <View key={s.user_id} style={styles.card}>
                <View style={styles.cardHeader}>
                  <View>
                    <Text style={styles.cardTitle}>{s.full_name}</Text>
                    <Text style={styles.cardEmail}>{s.email}</Text>
                  </View>
                  <View style={styles.scoreCircle}>
                    <Text style={styles.scoreCircleText}>{s.average_score}%</Text>
                  </View>
                </View>
                <View style={styles.statsGrid}>
                  <View style={styles.statBox}>
                    <Text style={styles.statValue}>{s.submissions_count}</Text>
                    <Text style={styles.statLabel}>Quizzes</Text>
                  </View>
                  <View style={styles.statBox}>
                    <Text style={styles.statValue}>{s.sessions_count || 0}</Text>
                    <Text style={styles.statLabel}>Sessions</Text>
                  </View>
                  <View style={styles.statBox}>
                    <Text style={styles.statValue}>{s.average_engagement || 0}</Text>
                    <Text style={styles.statLabel}>Engagement</Text>
                  </View>
                </View>
                <View style={styles.engagementBar}>
                  <View style={[styles.engagementFill, { width: `${Math.min(100, s.average_engagement || 0)}%` }]} />
                </View>
                {dsp && (dsp.avg_zcr != null || dsp.avg_energy != null || dsp.avg_reading_ratio != null) && (
                  <Text style={styles.dspRow}>
                    ZCR: {dsp.avg_zcr?.toFixed(2) ?? '–'} · Energy: {dsp.avg_energy ?? '–'} · Reading: {dsp.avg_reading_ratio ? (dsp.avg_reading_ratio * 100).toFixed(1) + '%' : '–'}
                  </Text>
                )}
              </View>
            );
          })
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
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📊</Text>
          <Text style={styles.empty}>No quiz scores yet. Complete assignments to see your scores.</Text>
        </View>
      ) : (
        <>
          {/* Student Score Summary */}
          <View style={styles.studentSummary}>
            <Text style={styles.studentSummaryLabel}>Average Score</Text>
            <Text style={styles.studentSummaryValue}>
              {Math.round(myScores.reduce((acc, s) => acc + (s.my_score || 0), 0) / myScores.length)}%
            </Text>
            <Text style={styles.studentSummarySubtext}>{myScores.length} quizzes completed</Text>
          </View>
          {myScores.map((a) => (
            <View key={a.id} style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{a.title}</Text>
                <Text style={[styles.scoreText, a.my_score >= 70 ? styles.scoreGood : styles.scoreLow]}>
                  {a.my_score}%
                </Text>
              </View>
              <View style={styles.scoreBar}>
                <View style={[styles.scoreBarFill, { width: `${a.my_score}%`, backgroundColor: a.my_score >= 70 ? '#2e7d32' : '#ed6c02' }]} />
              </View>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}

// Chart Styles
const chartStyles = StyleSheet.create({
  container: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16 },
  label: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 16 },
  barsContainer: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-around', height: 160 },
  barWrapper: { alignItems: 'center' },
  barValue: { fontSize: 10, color: '#666', marginBottom: 4 },
  bar: { width: '80%', backgroundColor: '#00BCD4', borderRadius: 4 },
  barLabel: { fontSize: 10, color: '#666', marginTop: 6, textAlign: 'center' },
});

// Ring Styles
const ringStyles = StyleSheet.create({
  container: { alignItems: 'center', flex: 1 },
  ring: { width: 70, height: 70, borderRadius: 35, borderWidth: 6, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f8f8f8' },
  value: { fontSize: 16, fontWeight: '700' },
  label: { fontSize: 12, color: '#333', marginTop: 8, fontWeight: '600' },
  sublabel: { fontSize: 10, color: '#888', marginTop: 2 },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  filterRow: { marginBottom: 16 },
  filterLabel: { fontSize: 14, color: '#666', marginBottom: 8, fontWeight: '500' },
  filterChip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, backgroundColor: '#e0e0e0', marginRight: 8 },
  filterChipActive: { backgroundColor: '#00BCD4' },
  filterChipText: { fontSize: 14, color: '#333', fontWeight: '500' },
  filterChipTextActive: { color: '#fff' },
  emptyContainer: { alignItems: 'center', paddingVertical: 40 },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  empty: { textAlign: 'center', color: '#666', paddingHorizontal: 24, lineHeight: 22 },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 12, marginTop: 8, color: '#333' },

  // Stats Cards Row
  statsCardsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  statsCard: { flex: 1, padding: 16, borderRadius: 12, marginHorizontal: 4, alignItems: 'center' },
  statsCardValue: { fontSize: 24, fontWeight: '700', color: '#fff' },
  statsCardLabel: { fontSize: 12, color: 'rgba(255,255,255,0.85)', marginTop: 4 },

  // Progress Rings
  ringsContainer: { flexDirection: 'row', justifyContent: 'space-around', backgroundColor: '#fff', borderRadius: 16, padding: 20, marginBottom: 16 },

  // Overall Card
  overallCard: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 16 },
  overallTitle: { fontSize: 14, fontWeight: '600', color: '#666', marginBottom: 12 },
  overallRow: { flexDirection: 'row', justifyContent: 'space-around' },
  overallItem: { alignItems: 'center' },
  overallValue: { fontSize: 20, fontWeight: '700', color: '#00BCD4' },
  overallLabel: { fontSize: 11, color: '#666', marginTop: 2 },

  // Student Card
  card: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  cardTitle: { fontSize: 17, fontWeight: '600', color: '#333' },
  cardEmail: { fontSize: 13, color: '#666', marginTop: 2 },
  scoreCircle: { width: 50, height: 50, borderRadius: 25, backgroundColor: '#00BCD4', justifyContent: 'center', alignItems: 'center' },
  scoreCircleText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  statsGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  statBox: { alignItems: 'center', flex: 1 },
  statValue: { fontSize: 18, fontWeight: '700', color: '#00BCD4' },
  statLabel: { fontSize: 11, color: '#666', marginTop: 2 },
  engagementBar: { height: 6, backgroundColor: '#e0e0e0', borderRadius: 3, overflow: 'hidden' },
  engagementFill: { height: '100%', backgroundColor: '#00BCD4', borderRadius: 3 },
  dspRow: { fontSize: 11, color: '#888', marginTop: 8 },

  // Student View
  studentSummary: { backgroundColor: '#00BCD4', padding: 24, borderRadius: 16, alignItems: 'center', marginBottom: 16 },
  studentSummaryLabel: { fontSize: 14, color: 'rgba(255,255,255,0.8)' },
  studentSummaryValue: { fontSize: 48, fontWeight: '700', color: '#fff', marginVertical: 8 },
  studentSummarySubtext: { fontSize: 14, color: 'rgba(255,255,255,0.8)' },
  scoreText: { fontSize: 22, fontWeight: '700' },
  scoreGood: { color: '#2e7d32' },
  scoreLow: { color: '#ed6c02' },
  scoreBar: { height: 8, backgroundColor: '#e0e0e0', borderRadius: 4, marginTop: 8, overflow: 'hidden' },
  scoreBarFill: { height: '100%', borderRadius: 4 },
});
