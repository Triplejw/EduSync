import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  TextInput,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';

export default function MaterialsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [materials, setMaterials] = useState<any[]>([]);
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');
  const [selectedClassroom, setSelectedClassroom] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [matRes, classRes] = await Promise.all([
        api.listMaterials(selectedClassroom ?? undefined),
        api.listClassrooms(),
      ]);
      setMaterials(matRes);
      setClassrooms(classRes);
    } catch (e) {
      console.error(e);
      Alert.alert('Error', 'Could not load materials');
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

  const processDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['image/*', 'application/pdf'],
      });
      if (result.canceled) return;

      const file = result.assets[0];
      setUploading(true);
      setStatus('Extracting text...');

      const text = await api.extractText({
        uri: file.uri,
        name: file.name,
        type: file.mimeType || 'application/pdf',
      });

      if (!text || text.length < 50) {
        Alert.alert('Error', 'Could not extract enough text from the document');
        setUploading(false);
        return;
      }

      setStatus('Generating AI summary...');
      const summary = await api.generateSummary(text);

      setStatus('Generating flashcards...');
      const flashcards = await api.generateFlashcards(text);

      setStatus('Generating quiz...');
      const quiz = await api.generateQuiz(text);

      const title = file.name.replace(/\.(pdf|jpg|jpeg|png)$/i, '') || 'Untitled';

      setStatus('Saving...');
      await api.createMaterial({
        title,
        summary,
        flashcards_json: typeof flashcards === 'string' ? flashcards : JSON.stringify(flashcards),
        quiz_json: typeof quiz === 'string' ? quiz : JSON.stringify(quiz),
        classroom_id: selectedClassroom ?? undefined,
        raw_text: text,
      });

      setStatus('Done!');
      loadData();
    } catch (e) {
      console.error(e);
      Alert.alert('Error', 'Processing failed. Check backend connection.');
    } finally {
      setUploading(false);
    }
  };

  const isTeacher = user?.role === 'teacher';

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

      {isTeacher && (
        <TouchableOpacity
          style={[styles.uploadBtn, uploading && styles.uploadBtnDisabled]}
          onPress={processDocument}
          disabled={uploading}
        >
          <Text style={styles.uploadBtnText}>
            {uploading ? status : '📤 Upload & Generate AI Content'}
          </Text>
        </TouchableOpacity>
      )}

      {uploading && <ActivityIndicator size="small" color="#0a7ea4" style={{ marginVertical: 8 }} />}

      {materials.length === 0 ? (
        <Text style={styles.empty}>No materials yet. {isTeacher ? 'Upload a document to get started.' : 'Materials will appear when your teacher adds them.'}</Text>
      ) : (
        materials.map((m) => (
          <TouchableOpacity
            key={m.id}
            style={styles.card}
            onPress={() => router.push(`/material/${m.id}`)}
          >
            <Text style={styles.cardTitle}>{m.title}</Text>
            <Text style={styles.cardSummary} numberOfLines={2}>
              {m.summary || 'No summary'}
            </Text>
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
  filterChipActive: { backgroundColor: '#0a7ea4' },
  filterChipText: { fontSize: 14, color: '#333' },
  filterChipTextActive: { color: '#fff' },
  uploadBtn: {
    backgroundColor: '#0a7ea4',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 20,
  },
  uploadBtnDisabled: { opacity: 0.7 },
  uploadBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
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
  cardSummary: { fontSize: 14, color: '#666', lineHeight: 20 },
});
