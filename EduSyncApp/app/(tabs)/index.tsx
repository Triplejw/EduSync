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
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';
import { getAuthErrorMessage } from '@/lib/authErrors';

/** Group materials by classroom_id for class-card layout. Keys: classroom id (number) or 'unassigned' (null). */
function groupMaterialsByClassroom(materials: any[]): Map<number | 'unassigned', any[]> {
  const map = new Map<number | 'unassigned', any[]>();
  const list = Array.isArray(materials) ? materials : (materials?.items ?? []);
  for (const m of list) {
    const key = m.classroom_id == null ? 'unassigned' : m.classroom_id;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(m);
  }
  return map;
}

export default function MaterialsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [materials, setMaterials] = useState<any[]>([]);
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [matRes, classRes] = await Promise.all([
        api.listMaterials(), // no filter – get all, then group by classroom_id
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
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  /** Open document picker and upload; use uploadTargetClassroomId if set (e.g. from "Upload to this class"). */
  const processDocument = useCallback(
    async (classroomId: number | null) => {
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
        setStatus('Uploading & processing...');
        setElapsedTime(0);

        timerRef.current = setInterval(() => {
          setElapsedTime((prev) => prev + 1);
        }, 1000);

        const material = await api.uploadMaterial(
          {
            uri: file.uri,
            name: file.name,
            type: file.mimeType || 'application/pdf',
          },
          undefined,
          classroomId ?? undefined
        );

        setStatus('Done!');
        Alert.alert('Success', `Material "${material.title}" created!`);
        loadData();
      } catch (e: any) {
        console.error('Upload error:', e);
        const errorMsg = getAuthErrorMessage(e, 'Upload failed');
        if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
          Alert.alert(
            'Timeout',
            'Upload is taking longer than expected. Please check if the material was created and try again.'
          );
        } else if (e?.message?.includes('Network Error')) {
          Alert.alert(
            'Network Error',
            'Lost connection to backend. Please check your connection and try again.'
          );
        } else {
          Alert.alert('Error', errorMsg);
        }
      } finally {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setUploading(false);
        setElapsedTime(0);
      }
    },
    [loadData]
  );

  /** For teachers: open picker and upload to this classroom. */
  const startUploadForClass = useCallback((classroomId: number) => {
    processDocument(classroomId);
  }, [processDocument]);

  const isTeacher = user?.role === 'teacher';
  const grouped = groupMaterialsByClassroom(materials);

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
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} />}
    >
      {uploading && (
        <View style={styles.uploadingInfo}>
          <ActivityIndicator size="small" color="#00BCD4" />
          <Text style={styles.uploadingText}>
            Uploading... {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
          </Text>
          <Text style={styles.uploadingHint}>Processing document text</Text>
        </View>
      )}

      {classrooms.length === 0 && !grouped.has('unassigned') ? (
        <Text style={styles.empty}>
          {isTeacher ? 'Create a classroom (Classrooms tab), then add materials here.' : 'Join a classroom with a code from your teacher.'}
        </Text>
      ) : (
        <>
          {/* Class cards: one per classroom */}
          {classrooms.map((c) => {
            const classMats = grouped.get(c.id) || [];
            return (
              <View key={c.id} style={styles.classCard}>
                <View style={styles.classCardHeader}>
                  <Text style={styles.classCardTitle}>{c.name}</Text>
                  {isTeacher && <Text style={styles.classCardCode}>Code: {c.code}</Text>}
                </View>
                {classMats.length === 0 ? (
                  <Text style={styles.classEmpty}>No materials yet.</Text>
                ) : (
                  classMats.map((m) => (
                    <TouchableOpacity
                      key={m.id}
                      style={styles.materialCard}
                      onPress={() => router.push(`/material/${m.id}`)}
                    >
                      <Text style={styles.materialCardTitle}>{m.title}</Text>
                      <Text style={styles.materialCardSummary} numberOfLines={2}>
                        {m.summary || 'No summary'}
                      </Text>
                    </TouchableOpacity>
                  ))
                )}
                {isTeacher && (
                  <TouchableOpacity
                    style={[styles.uploadToClassBtn, uploading && styles.uploadBtnDisabled]}
                    onPress={() => startUploadForClass(c.id)}
                    disabled={uploading}
                  >
                    <Text style={styles.uploadToClassBtnText}>Upload to this class</Text>
                  </TouchableOpacity>
                )}
              </View>
            );
          })}

          {/* Unassigned materials (teachers only) */}
          {isTeacher && grouped.has('unassigned') && (grouped.get('unassigned')!.length > 0) && (
            <View style={styles.classCard}>
              <View style={styles.classCardHeader}>
                <Text style={styles.classCardTitle}>Unassigned</Text>
                <Text style={styles.classCardCode}>Materials not in a class</Text>
              </View>
              {(grouped.get('unassigned') || []).map((m: any) => (
                <TouchableOpacity
                  key={m.id}
                  style={styles.materialCard}
                  onPress={() => router.push(`/material/${m.id}`)}
                >
                  <Text style={styles.materialCardTitle}>{m.title}</Text>
                  <Text style={styles.materialCardSummary} numberOfLines={2}>
                    {m.summary || 'No summary'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  uploadingInfo: {
    alignItems: 'center',
    marginBottom: 16,
    padding: 16,
    backgroundColor: '#e8f4f8',
    borderRadius: 12,
  },
  uploadingText: { marginTop: 8, fontSize: 14, color: '#00BCD4', fontWeight: '500' },
  uploadingHint: { marginTop: 4, fontSize: 12, color: '#666' },
  uploadBtnDisabled: { opacity: 0.7 },
  empty: { textAlign: 'center', color: '#666', marginTop: 40, paddingHorizontal: 24 },
  classCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    marginBottom: 20,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  classCardHeader: { marginBottom: 12 },
  classCardTitle: { fontSize: 20, fontWeight: '700', color: '#1a1a1a' },
  classCardCode: { fontSize: 13, color: '#00BCD4', marginTop: 4 },
  classEmpty: { fontSize: 14, color: '#888', marginBottom: 12 },
  materialCard: {
    backgroundColor: '#f8fafc',
    padding: 14,
    borderRadius: 12,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#00BCD4',
  },
  materialCardTitle: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 4 },
  materialCardSummary: { fontSize: 14, color: '#666', lineHeight: 20 },
  uploadToClassBtn: {
    backgroundColor: '#00BCD4',
    padding: 12,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  uploadToClassBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
});
