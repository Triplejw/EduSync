import { useState, useEffect, useCallback, useRef } from 'react';
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
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';
import { getAuthErrorMessage } from '@/lib/authErrors';

export default function ClassroomDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [classroom, setClassroom] = useState<any>(null);
  const [materials, setMaterials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const classroomId = id ? parseInt(id, 10) : null;
  const isTeacher = user?.role === 'teacher';

  const loadData = useCallback(async () => {
    if (!classroomId) return;
    try {
      const [classroomRes, materialsRes] = await Promise.all([
        api.getClassroom(classroomId),
        api.listMaterials(classroomId),
      ]);
      setClassroom(classroomRes);
      setMaterials(materialsRes);
    } catch (e) {
      console.error(e);
      Alert.alert('Error', 'Could not load classroom');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [classroomId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const uploadDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          'image/*',
          'application/pdf',
          'application/vnd.ms-powerpoint',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        ],
      });
      if (result.canceled) return;

      const file = result.assets[0];
      setUploading(true);
      setStatus('Uploading...');
      setElapsedTime(0);

      timerRef.current = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);

      const material = await api.uploadMaterial(
        { uri: file.uri, name: file.name, type: file.mimeType || 'application/pdf' },
        undefined,
        classroomId ?? undefined
      );

      setStatus('Done!');
      Alert.alert('Success', `Material "${material.title}" uploaded!`);
      loadData();
    } catch (e: any) {
      console.error('Upload error:', e);
      const errorMsg = getAuthErrorMessage(e, 'Upload failed');
      Alert.alert('Error', errorMsg);
    } finally {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setUploading(false);
      setElapsedTime(0);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#00BCD4" />
      </View>
    );
  }

  if (!classroom) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Classroom not found</Text>
        <TouchableOpacity style={styles.backBtnContainer} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>{classroom.name}</Text>
        {classroom.subject_name && (
          <Text style={styles.subtitle}>{classroom.subject_name}</Text>
        )}
        <View style={styles.headerMeta}>
          {isTeacher ? (
            <Text style={styles.metaText}>Code: {classroom.code}</Text>
          ) : (
            <Text style={styles.metaText}>Teacher: {classroom.teacher_name || 'Unknown'}</Text>
          )}
          <Text style={styles.metaText}>{classroom.student_count || 0} students</Text>
          <Text style={styles.metaText}>{classroom.material_count || 0} materials</Text>
        </View>
      </View>

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentInner}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Upload button for teachers */}
        {isTeacher && (
          <TouchableOpacity
            style={[styles.uploadBtn, uploading && styles.uploadBtnDisabled]}
            onPress={uploadDocument}
            disabled={uploading}
          >
            <Text style={styles.uploadBtnText}>
              {uploading ? status : '+ Upload Study Material'}
            </Text>
          </TouchableOpacity>
        )}

        {uploading && (
          <View style={styles.uploadingInfo}>
            <ActivityIndicator size="small" color="#00BCD4" />
            <Text style={styles.uploadingText}>
              Uploading... {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
            </Text>
          </View>
        )}

        {/* Materials list */}
        <Text style={styles.sectionTitle}>Study Materials</Text>
        {materials.length === 0 ? (
          <Text style={styles.empty}>
            {isTeacher
              ? 'No materials yet. Upload a document to get started.'
              : 'No materials uploaded yet.'}
          </Text>
        ) : (
          materials.map((m) => (
            <TouchableOpacity
              key={m.id}
              style={styles.materialCard}
              onPress={() => router.push(`/material/${m.id}`)}
            >
              <Text style={styles.materialTitle}>{m.title}</Text>
              <Text style={styles.materialMeta}>
                {m.summary ? 'Summary available' : 'No summary yet'}
                {' • '}
                {m.flashcards_json && m.flashcards_json !== '[]' ? 'Flashcards ready' : 'No flashcards yet'}
              </Text>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  errorText: { fontSize: 16, color: '#666', marginBottom: 16 },
  backBtnContainer: { padding: 12, backgroundColor: '#00BCD4', borderRadius: 8 },
  backBtnText: { color: '#fff', fontWeight: '600' },
  header: {
    backgroundColor: '#00BCD4',
    padding: 16,
    paddingTop: 50,
  },
  backBtn: { fontSize: 16, color: '#fff', marginBottom: 8 },
  title: { fontSize: 24, fontWeight: '700', color: '#fff' },
  subtitle: { fontSize: 16, color: 'rgba(255,255,255,0.8)', marginTop: 4 },
  headerMeta: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 12, gap: 12 },
  metaText: { fontSize: 13, color: 'rgba(255,255,255,0.9)', backgroundColor: 'rgba(255,255,255,0.15)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  content: { flex: 1 },
  contentInner: { padding: 16, paddingBottom: 40 },
  uploadBtn: {
    backgroundColor: '#00BCD4',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 20,
  },
  uploadBtnDisabled: { opacity: 0.7 },
  uploadBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  uploadingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#e8f4f8',
    borderRadius: 8,
  },
  uploadingText: { marginLeft: 8, fontSize: 14, color: '#00BCD4' },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 12 },
  empty: { textAlign: 'center', color: '#666', marginTop: 20, paddingHorizontal: 24 },
  materialCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#00BCD4',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  materialTitle: { fontSize: 17, fontWeight: '600', color: '#333', marginBottom: 6 },
  materialMeta: { fontSize: 13, color: '#888' },
});
