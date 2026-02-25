import { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';
import { AttentionTracker } from '@/components/AttentionTracker';

export default function AssignmentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [assignment, setAssignment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submissions, setSubmissions] = useState<any[]>([]);

  useEffect(() => {
    if (!id) return;
    api.getAssignment(parseInt(id, 10)).then(setAssignment).catch(() => Alert.alert('Error', 'Could not load assignment')).finally(() => setLoading(false));
    if (user?.role === 'teacher') {
      api.getAssignmentSubmissions(parseInt(id, 10)).then((d) => setSubmissions(d.submissions || [])).catch(() => {});
    }
  }, [id, user?.role]);

  const quiz = (() => {
    try {
      const j = assignment?.quiz_json;
      if (!j) return [];
      return typeof j === 'string' ? JSON.parse(j) : j;
    } catch {
      return [];
    }
  })();

  const isTeacher = user?.role === 'teacher';

  const handleSubmit = async () => {
    const answered = Object.keys(answers).length;
    if (answered < quiz.length) {
      Alert.alert('Incomplete', `You answered ${answered} of ${quiz.length} questions.`);
      return;
    }
    setSubmitting(true);
    try {
      const answerList = quiz.map((_: any, i: number) => ({
        question_index: i,
        selected_answer_index: answers[i] ?? 0,
      }));
      const result = await api.submitQuiz(parseInt(id!, 10), answerList);
      Alert.alert('Submitted!', `Your score: ${result.score.toFixed(0)}%`);
      router.back();
    } catch (e) {
      Alert.alert('Error', 'Could not submit. You may have already submitted.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !assignment) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#00BCD4" />
      </View>
    );
  }

  if (isTeacher) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.backBtn}>← Back</Text>
          </TouchableOpacity>
          <Text style={styles.title}>{assignment.title}</Text>
        </View>
        <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
          <Text style={styles.sectionTitle}>Submissions ({submissions.length})</Text>
          {submissions.length === 0 ? (
            <Text style={styles.empty}>No submissions yet.</Text>
          ) : (
            submissions.map((s) => (
              <View key={s.user_id} style={styles.card}>
                <Text style={styles.cardTitle}>{s.full_name}</Text>
                <Text style={styles.cardEmail}>{s.email}</Text>
                <Text style={styles.scoreText}>{s.score}%</Text>
              </View>
            ))
          )}
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {quiz.length > 0 && id && (
        <AttentionTracker
          studentId={user?.id?.toString() ?? 'unknown'}
          assignmentId={parseInt(id, 10)}
        />
      )}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>{assignment.title}</Text>
      </View>
      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {quiz.map((q: any, i: number) => (
          <View key={i} style={styles.questionCard}>
            <Text style={styles.questionText}>{i + 1}. {q.question}</Text>
            <View style={styles.options}>
              {(q.options || []).map((opt: string, j: number) => (
                <TouchableOpacity
                  key={j}
                  style={[styles.option, answers[i] === j && styles.optionSelected]}
                  onPress={() => setAnswers((prev) => ({ ...prev, [i]: j }))}
                >
                  <Text style={[styles.optionText, answers[i] === j && styles.optionTextSelected]}>
                    {String.fromCharCode(65 + j)}. {opt}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ))}
      </ScrollView>
      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          <Text style={styles.submitBtnText}>{submitting ? 'Submitting...' : 'Submit Quiz'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { backgroundColor: '#fff', padding: 16, paddingTop: 50, borderBottomWidth: 1, borderColor: '#eee' },
  backBtn: { fontSize: 16, color: '#00BCD4', marginBottom: 8 },
  title: { fontSize: 22, fontWeight: '600', color: '#333' },
  content: { flex: 1 },
  contentInner: { padding: 16, paddingBottom: 100 },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 16, color: '#333' },
  empty: { textAlign: 'center', color: '#666', marginTop: 20 },
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
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 4 },
  cardEmail: { fontSize: 14, color: '#666', marginBottom: 4 },
  scoreText: { fontSize: 20, color: '#00BCD4', fontWeight: '700' },
  questionCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  questionText: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 12, lineHeight: 24 },
  options: { gap: 8 },
  option: {
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  optionSelected: { borderColor: '#00BCD4', backgroundColor: '#e8f4f8' },
  optionText: { fontSize: 15, color: '#333' },
  optionTextSelected: { color: '#00BCD4', fontWeight: '500' },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    padding: 16,
    borderTopWidth: 1,
    borderColor: '#eee',
  },
  submitBtn: {
    backgroundColor: '#00BCD4',
    padding: 16,
    borderRadius: 10,
    alignItems: 'center',
  },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
