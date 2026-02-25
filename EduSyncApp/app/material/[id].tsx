import { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Dimensions,
  Animated,
  Platform,
} from 'react-native';
import { Image } from 'expo-image';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system/legacy';
import { WebView } from 'react-native-webview';
import { useLocalSearchParams, useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '@/context/AuthContext';
import * as api from '@/lib/api';
import { useScrollTracker } from '@/hooks/useScrollTracker';

type TabType = 'document' | 'summary' | 'flashcards';

/** Returns HTML string that loads PDF.js from CDN and renders the PDF from base64. */
function getPdfViewerHtml(base64: string): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=2.0, user-scalable=yes" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
  <style>
    body { margin: 0; padding: 8px; background: #525659; }
    canvas { display: block; margin: 8px auto; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
    .loading { color: #fff; text-align: center; padding: 24px; }
  </style>
</head>
<body>
  <div id="container"></div>
  <div id="loading" class="loading">Loading PDF...</div>
  <script>
    var base64 = "${base64}";
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    var url = 'data:application/pdf;base64,' + base64;
    pdfjsLib.getDocument(url).promise.then(function(pdf) {
      document.getElementById('loading').style.display = 'none';
      var container = document.getElementById('container');
      for (var i = 1; i <= pdf.numPages; i++) {
        pdf.getPage(i).then(function(page) {
          var scale = 1.5;
          var viewport = page.getViewport({ scale: scale });
          var canvas = document.createElement('canvas');
          var ctx = canvas.getContext('2d');
          canvas.height = viewport.height;
          canvas.width = viewport.width;
          container.appendChild(canvas);
          page.render({ canvasContext: ctx, viewport: viewport });
        });
      }
    }).catch(function(err) {
      document.getElementById('loading').textContent = 'Failed to load PDF: ' + (err.message || 'Unknown error');
    });
    // Report scroll position every 1s for engagement signal (DSP 1 Hz sampling)
    setInterval(function() {
      var scrollTop = window.pageYOffset !== undefined ? window.pageYOffset : document.documentElement.scrollTop;
      if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'pdfScroll', scrollTop: scrollTop }));
      }
    }, 1000);
  </script>
</body>
</html>`;
}

export default function MaterialDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [material, setMaterial] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('document');
  const [cardIndex, setCardIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const flipAnim = useRef(new Animated.Value(0)).current;
  const [classrooms, setClassrooms] = useState<any[]>([]);
  const [selectedClassroom, setSelectedClassroom] = useState<number | null>(null);
  const [generating, setGenerating] = useState<'summary' | 'flashcards' | 'quiz' | null>(null);
  const [localFileUri, setLocalFileUri] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [pdfBase64, setPdfBase64] = useState<string | null>(null);

  // Multimodal engagement: scroll tracking (1Hz) for DSP-based engagement analytics.
  // Native ScrollView (summary/flashcards) uses onScroll; PDF WebView uses postMessage + pushDelta.
  const { onScroll, getScrollSignal, reset, pushDelta } = useScrollTracker();
  const isStudent = user?.role === 'student';
  const isTeacher = user?.role === 'teacher';
  const analyticsSubmitted = useRef(false);
  const lastPdfScrollTop = useRef(0);

  const loadMaterial = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.getMaterial(parseInt(id, 10));
      setMaterial(data);
    } catch (e) {
      Alert.alert('Error', 'Could not load material');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadMaterial();
    api.listClassrooms().then(setClassrooms);
    reset();
    analyticsSubmitted.current = false;
    lastPdfScrollTop.current = 0;
  }, [loadMaterial, reset]);

  const handlePdfScrollMessage = useCallback(
    (event: { nativeEvent: { data: string } }) => {
      if (!isStudent || activeTab !== 'document') return;
      try {
        const data = JSON.parse(event.nativeEvent.data);
        if (data?.type === 'pdfScroll' && typeof data.scrollTop === 'number') {
          const delta = Math.abs(data.scrollTop - lastPdfScrollTop.current);
          pushDelta(delta);
          lastPdfScrollTop.current = data.scrollTop;
        }
      } catch {
        // ignore malformed messages
      }
    },
    [isStudent, activeTab, pushDelta]
  );

  const submitScrollAnalytics = useCallback(async () => {
    if (!isStudent || !material?.id || analyticsSubmitted.current) return;
    const signal = getScrollSignal();
    if (signal.length < 3) return;
    analyticsSubmitted.current = true;
    try {
      await api.submitAnalytics(material.id, signal);
    } catch (e) {
      console.warn('Failed to submit analytics:', e);
    }
  }, [isStudent, material?.id, getScrollSignal]);

  useFocusEffect(
    useCallback(() => {
      return () => {
        submitScrollAnalytics();
      };
    }, [submitScrollAnalytics])
  );

  const flashcards = (() => {
    try {
      const j = material?.flashcards_json;
      if (!j) return [];
      const parsed = typeof j === 'string' ? JSON.parse(j) : j;
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  })();

  const quizQuestions = (() => {
    try {
      const j = material?.quiz_json;
      if (!j) return [];
      const parsed = typeof j === 'string' ? JSON.parse(j) : j;
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  })();

  const handleFlipCard = useCallback(() => {
    const next = !showAnswer;
    setShowAnswer(next);
    Animated.spring(flipAnim, {
      toValue: next ? 1 : 0,
      useNativeDriver: true,
      friction: 8,
      tension: 80,
    }).start();
  }, [showAnswer, flipAnim]);

  const goPrev = useCallback(() => {
    setCardIndex((i) => Math.max(0, i - 1));
    setShowAnswer(false);
    flipAnim.setValue(0);
  }, [flipAnim]);

  const goNext = useCallback(() => {
    setCardIndex((i) => Math.min(flashcards.length - 1, i + 1));
    setShowAnswer(false);
    flipAnim.setValue(0);
  }, [flashcards.length, flipAnim]);

  const handleGenerateSummary = async () => {
    if (!material?.id) return;
    setGenerating('summary');
    try {
      const result = await api.generateMaterialSummary(material.id);
      setMaterial((prev: any) => ({ ...prev, summary: result.summary }));
      Alert.alert('Success', result.cached ? 'Summary loaded from cache.' : 'Summary generated!');
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'Failed to generate summary');
    } finally {
      setGenerating(null);
    }
  };

  const handleGenerateFlashcards = async () => {
    if (!material?.id) return;
    setGenerating('flashcards');
    try {
      const result = await api.generateMaterialFlashcards(material.id);
      setMaterial((prev: any) => ({ ...prev, flashcards_json: result.flashcards }));
      Alert.alert('Success', result.cached ? 'Flashcards loaded from cache.' : 'Flashcards generated!');
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'Failed to generate flashcards');
    } finally {
      setGenerating(null);
    }
  };

  const handleGenerateQuiz = async () => {
    if (!material?.id) return;
    setGenerating('quiz');
    try {
      const result = await api.generateMaterialQuiz(material.id);
      setMaterial((prev: any) => ({ ...prev, quiz_json: result.quiz }));
      Alert.alert('Success', result.cached ? 'Quiz loaded from cache.' : 'Quiz generated!');
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'Failed to generate quiz');
    } finally {
      setGenerating(null);
    }
  };

  const handleCreateAssignment = async () => {
    if (!selectedClassroom) {
      Alert.alert('Error', 'Select a classroom first');
      return;
    }
    if (quizQuestions.length === 0) {
      Alert.alert('Error', 'Generate a quiz first');
      return;
    }
    try {
      const quizStr = typeof material.quiz_json === 'string' ? material.quiz_json : JSON.stringify(material.quiz_json);
      await api.createAssignment({
        title: `${material.title} - Quiz`,
        quiz_json: quizStr,
        classroom_id: selectedClassroom,
        material_id: material.id,
      });
      Alert.alert('Success', 'Assignment posted to students!');
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const msg = Array.isArray(detail) ? detail.join(' ') : (typeof detail === 'string' ? detail : null) ?? e?.message ?? 'Could not create assignment';
      Alert.alert('Error', typeof msg === 'string' ? msg : 'Could not create assignment');
    }
  };

  const runDownload = useCallback(async (): Promise<string | null> => {
    if (!material?.file_path || !material?.id) return null;
    setDownloadError(null);
    setDownloading(true);
    try {
      const fileExt = '.' + (material.file_path?.split('.').pop()?.toLowerCase() || 'pdf');
      const uri = await api.downloadMaterialFile(material.id, fileExt);
      setLocalFileUri(uri);
      return uri;
    } catch (e: any) {
      console.error('Download error:', e);
      setDownloadError(e?.message || 'Could not download document. Check connection and try again.');
      return null;
    } finally {
      setDownloading(false);
    }
  }, [material?.id, material?.file_path]);

  const downloadAndOpenDocument = async () => {
    if (!material?.file_path) {
      Alert.alert('Error', 'No document available');
      return;
    }
    if (localFileUri) {
      openLocalFile(localFileUri);
      return;
    }
    const uri = await runDownload();
    if (uri) openLocalFile(uri);
  };

  const retryDownload = useCallback(() => {
    setDownloadError(null);
    setLocalFileUri(null);
    setPdfBase64(null);
    runDownload();
  }, [runDownload]);

  const openLocalFile = async (uri: string) => {
    try {
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(uri, {
          mimeType: getMimeType(material.file_path),
          dialogTitle: 'Open Document',
        });
      } else {
        Alert.alert('Error', 'Sharing is not available on this device');
      }
    } catch (e) {
      console.error('Share error:', e);
      Alert.alert('Error', 'Could not open document');
    }
  };

  const getMimeType = (filePath: string): string => {
    const ext = filePath?.split('.').pop()?.toLowerCase() || '';
    const mimeTypes: Record<string, string> = {
      pdf: 'application/pdf',
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      png: 'image/png',
      gif: 'image/gif',
      webp: 'image/webp',
      ppt: 'application/vnd.ms-powerpoint',
      pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    };
    return mimeTypes[ext] || 'application/octet-stream';
  };

  // Download file when document tab is active and file not yet downloaded
  useEffect(() => {
    if (activeTab === 'document' && material?.file_path && !localFileUri && !downloading && !downloadError) {
      runDownload();
    }
  }, [activeTab, material?.file_path, material?.id, localFileUri, downloading, downloadError, runDownload]);

  // Read PDF as base64 when we have cached file (for in-app WebView viewer)
  const fileExtForPdf = material?.file_path?.split('.').pop()?.toLowerCase() || '';
  const isPdf = fileExtForPdf === 'pdf';
  useEffect(() => {
    if (!localFileUri || !isPdf) {
      setPdfBase64(null);
      return;
    }
    let cancelled = false;
    FileSystem.readAsStringAsync(localFileUri, { encoding: FileSystem.EncodingType.Base64 })
      .then((b64) => {
        if (!cancelled) setPdfBase64(b64);
      })
      .catch(() => {
        if (!cancelled) setPdfBase64(null);
      });
    return () => { cancelled = true; };
  }, [localFileUri, isPdf]);

  if (loading || !material) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#00BCD4" />
      </View>
    );
  }

  const { width } = Dimensions.get('window');
  const fileExt = material.file_path?.split('.').pop()?.toLowerCase() || '';
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileExt);
  const isPdfRender = fileExt === 'pdf';

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={2}>{material.title}</Text>
      </View>

      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'document' && styles.tabActive]}
          onPress={() => setActiveTab('document')}
        >
          <Text style={[styles.tabText, activeTab === 'document' && styles.tabTextActive]}>Document</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'summary' && styles.tabActive]}
          onPress={() => setActiveTab('summary')}
        >
          <Text style={[styles.tabText, activeTab === 'summary' && styles.tabTextActive]}>Summary</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'flashcards' && styles.tabActive]}
          onPress={() => setActiveTab('flashcards')}
        >
          <Text style={[styles.tabText, activeTab === 'flashcards' && styles.tabTextActive]}>Flashcards</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentInner}
        onScroll={
          isStudent && !(activeTab === 'document' && pdfBase64) ? onScroll : undefined
        }
        scrollEventThrottle={
          isStudent && !(activeTab === 'document' && pdfBase64) ? 100 : undefined
        }
      >
        {/* Document Tab */}
        {activeTab === 'document' && (
          <View style={styles.documentContainer}>
            {downloadError ? (
              <View style={styles.documentPlaceholder}>
                <Text style={styles.documentIcon}>⚠️</Text>
                <Text style={styles.downloadErrorText}>{downloadError}</Text>
                <TouchableOpacity style={styles.openBtn} onPress={retryDownload}>
                  <Text style={styles.openBtnText}>Retry</Text>
                </TouchableOpacity>
              </View>
            ) : downloading ? (
              <View style={styles.documentPlaceholder}>
                <ActivityIndicator size="large" color="#00BCD4" />
                <Text style={styles.downloadingText}>Downloading document...</Text>
              </View>
            ) : isImage && localFileUri ? (
              <Image
                source={{ uri: localFileUri }}
                style={styles.documentImage}
                contentFit="contain"
              />
            ) : isPdfRender && localFileUri ? (
              <View style={styles.pdfViewerWrap}>
                {pdfBase64 ? (
                  <WebView
                    originWhitelist={['*']}
                    source={{ html: getPdfViewerHtml(pdfBase64) }}
                    style={styles.pdfWebView}
                    scalesPageToFit
                    scrollEnabled
                    onMessage={handlePdfScrollMessage}
                    {...(Platform.OS === 'android' && { androidLayerType: 'hardware' })}
                  />
                ) : (
                  <View style={styles.documentPlaceholder}>
                    <ActivityIndicator size="large" color="#00BCD4" />
                    <Text style={styles.downloadingText}>Loading PDF...</Text>
                  </View>
                )}
                <TouchableOpacity style={styles.openExternalLink} onPress={() => openLocalFile(localFileUri)}>
                  <Text style={styles.openExternalLinkText}>Open in external app</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.documentPlaceholder}>
                <Text style={styles.documentIcon}>📄</Text>
                <Text style={styles.documentName}>{material.title}</Text>
                <Text style={styles.documentType}>{fileExt.toUpperCase() || 'Document'}</Text>
                {!material.file_path ? (
                  <Text style={styles.noDocumentText}>No document uploaded</Text>
                ) : (
                  <TouchableOpacity
                    style={[styles.openBtn, downloading && styles.openBtnDisabled]}
                    onPress={downloadAndOpenDocument}
                    disabled={downloading}
                  >
                    <Text style={styles.openBtnText}>
                      {localFileUri ? 'Open Document' : 'Download & Open'}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
          </View>
        )}

        {/* Summary Tab */}
        {activeTab === 'summary' && (
          <View>
            {material.summary && material.summary.length > 10 ? (
              <Text style={styles.summary}>{material.summary}</Text>
            ) : (
              <View style={styles.generateContainer}>
                <Text style={styles.generateIcon}>📝</Text>
                <Text style={styles.generateText}>No summary yet.</Text>
                <TouchableOpacity
                  style={[styles.generateBtn, generating === 'summary' && styles.generateBtnDisabled]}
                  onPress={handleGenerateSummary}
                  disabled={generating !== null}
                >
                  {generating === 'summary' ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.generateBtnText}>Generate Summary</Text>
                  )}
                </TouchableOpacity>
                {generating === 'summary' && (
                  <Text style={styles.generatingHint}>This may take 30-60 seconds...</Text>
                )}
              </View>
            )}
          </View>
        )}

        {/* Flashcards Tab */}
        {activeTab === 'flashcards' && (
          <View style={styles.flashcardContainer}>
            {flashcards.length === 0 ? (
              <View style={styles.generateContainer}>
                <Text style={styles.generateIcon}>🎴</Text>
                <Text style={styles.generateText}>No flashcards yet.</Text>
                <TouchableOpacity
                  style={[styles.generateBtn, generating === 'flashcards' && styles.generateBtnDisabled]}
                  onPress={handleGenerateFlashcards}
                  disabled={generating !== null}
                >
                  {generating === 'flashcards' ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.generateBtnText}>Generate Flashcards</Text>
                  )}
                </TouchableOpacity>
                {generating === 'flashcards' && (
                  <Text style={styles.generatingHint}>This may take 30-60 seconds...</Text>
                )}
              </View>
            ) : (
              <>
                <TouchableOpacity
                  activeOpacity={1}
                  onPress={handleFlipCard}
                  style={[styles.flashcardWrapper, { width: width - 48 }]}
                >
                  <Animated.View
                    style={[
                      styles.flashcardFace,
                      styles.flashcardFront,
                      {
                        opacity: flipAnim.interpolate({
                          inputRange: [0, 0.5, 1],
                          outputRange: [1, 0, 0],
                        }),
                      },
                    ]}
                  >
                    <Text style={styles.cardLabel}>Question</Text>
                    <Text style={styles.cardText}>{flashcards[cardIndex]?.front ?? ''}</Text>
                    <Text style={styles.tapHint}>Tap to flip</Text>
                  </Animated.View>
                  <Animated.View
                    style={[
                      styles.flashcardFace,
                      styles.flashcardBack,
                      {
                        opacity: flipAnim.interpolate({
                          inputRange: [0, 0.5, 1],
                          outputRange: [0, 0, 1],
                        }),
                      },
                    ]}
                  >
                    <Text style={styles.cardLabelBack}>Answer</Text>
                    <Text style={styles.cardTextBack}>{flashcards[cardIndex]?.back ?? ''}</Text>
                    <Text style={styles.tapHintBack}>Tap to flip back</Text>
                  </Animated.View>
                </TouchableOpacity>
                <View style={styles.progressBarWrap}>
                  <View style={[styles.progressBarFill, { width: `${((cardIndex + 1) / flashcards.length) * 100}%` }]} />
                </View>
                <Text style={styles.cardCounter}>{cardIndex + 1} / {flashcards.length}</Text>
                <View style={styles.cardNav}>
                  <TouchableOpacity
                    style={[styles.navBtn, cardIndex === 0 && styles.navBtnDisabled]}
                    onPress={goPrev}
                    disabled={cardIndex === 0}
                  >
                    <Text style={styles.navBtnText}>← Prev</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.navBtn, cardIndex >= flashcards.length - 1 && styles.navBtnDisabled]}
                    onPress={goNext}
                    disabled={cardIndex >= flashcards.length - 1}
                  >
                    <Text style={styles.navBtnText}>Next →</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        )}
      </ScrollView>

      {/* Teacher Footer: Generate Quiz & Post Assignment */}
      {isTeacher && (
        <View style={styles.footer}>
          {quizQuestions.length === 0 ? (
            <TouchableOpacity
              style={[styles.generateQuizBtn, generating === 'quiz' && styles.generateBtnDisabled]}
              onPress={handleGenerateQuiz}
              disabled={generating !== null}
            >
              {generating === 'quiz' ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.generateQuizBtnText}>Generate Quiz from Content</Text>
              )}
            </TouchableOpacity>
          ) : (
            <>
              <Text style={styles.footerLabel}>Post quiz as assignment:</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.classroomPicker}>
                {classrooms.map((c) => (
                  <TouchableOpacity
                    key={c.id}
                    style={[styles.classroomChip, selectedClassroom === c.id && styles.classroomChipActive]}
                    onPress={() => setSelectedClassroom(c.id)}
                  >
                    <Text style={[styles.classroomChipText, selectedClassroom === c.id && styles.classroomChipTextActive]}>
                      {c.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TouchableOpacity
                style={[styles.postBtn, !selectedClassroom && styles.postBtnDisabled]}
                onPress={handleCreateAssignment}
                disabled={!selectedClassroom}
              >
                <Text style={styles.postBtnText}>Post Quiz as Assignment</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f6f8' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { backgroundColor: '#fff', padding: 16, paddingTop: 50, borderBottomWidth: 1, borderColor: '#eee' },
  backBtn: { fontSize: 16, color: '#00BCD4', marginBottom: 8 },
  title: { fontSize: 22, fontWeight: '600', color: '#333' },
  tabs: { flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderColor: '#eee' },
  tab: { flex: 1, padding: 12, alignItems: 'center' },
  tabActive: { borderBottomWidth: 3, borderBottomColor: '#00BCD4' },
  tabText: { fontSize: 14, color: '#666' },
  tabTextActive: { color: '#00BCD4', fontWeight: '600' },
  content: { flex: 1 },
  contentInner: { padding: 20, paddingBottom: 40 },
  // Document tab
  documentContainer: { alignItems: 'center' },
  documentImage: { width: '100%', height: 400, borderRadius: 12 },
  documentPlaceholder: { alignItems: 'center', padding: 40, backgroundColor: '#fff', borderRadius: 16, width: '100%' },
  documentIcon: { fontSize: 64, marginBottom: 16 },
  documentName: { fontSize: 18, fontWeight: '600', color: '#333', textAlign: 'center', marginBottom: 8 },
  documentType: { fontSize: 14, color: '#666', marginBottom: 20 },
  downloadingText: { marginTop: 16, fontSize: 16, color: '#666' },
  downloadErrorText: { marginTop: 8, marginBottom: 20, fontSize: 15, color: '#c62828', textAlign: 'center', paddingHorizontal: 16 },
  noDocumentText: { fontSize: 14, color: '#999', fontStyle: 'italic' },
  pdfViewerWrap: { width: '100%', flex: 1, minHeight: 500 },
  pdfWebView: { width: '100%', minHeight: 500, backgroundColor: '#525659', borderRadius: 12 },
  openExternalLink: { marginTop: 12, paddingVertical: 10, alignItems: 'center' },
  openExternalLinkText: { fontSize: 14, color: '#00BCD4', fontWeight: '600' },
  openBtn: { backgroundColor: '#00BCD4', paddingVertical: 14, paddingHorizontal: 32, borderRadius: 12 },
  openBtnDisabled: { opacity: 0.7 },
  openBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  // Summary tab
  summary: { fontSize: 16, lineHeight: 26, color: '#333' },
  // Generate buttons
  generateContainer: { alignItems: 'center', paddingVertical: 40 },
  generateIcon: { fontSize: 48, marginBottom: 16 },
  generateText: { fontSize: 16, color: '#666', marginBottom: 20, textAlign: 'center' },
  generateBtn: { backgroundColor: '#00BCD4', paddingVertical: 14, paddingHorizontal: 32, borderRadius: 12, minWidth: 200, alignItems: 'center' },
  generateBtnDisabled: { opacity: 0.7 },
  generateBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  generatingHint: { marginTop: 12, fontSize: 13, color: '#888' },
  // Flashcards
  flashcardContainer: { alignItems: 'center' },
  flashcardWrapper: { minHeight: 220, width: '100%', position: 'relative' },
  flashcardFace: {
    position: 'absolute', left: 0, right: 0, top: 0, minHeight: 220, padding: 24, borderRadius: 16, justifyContent: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.12, shadowRadius: 8, elevation: 4,
  },
  flashcardFront: { backgroundColor: '#e3f2fd', borderWidth: 2, borderColor: '#00BCD4' },
  flashcardBack: { backgroundColor: '#e8f5e9', borderWidth: 2, borderColor: '#2e7d32' },
  cardLabel: { fontSize: 12, color: '#00BCD4', marginBottom: 12, textTransform: 'uppercase', fontWeight: '700' },
  cardText: { fontSize: 19, lineHeight: 28, color: '#1a1a1a' },
  cardLabelBack: { fontSize: 12, color: '#2e7d32', marginBottom: 12, textTransform: 'uppercase', fontWeight: '700' },
  cardTextBack: { fontSize: 19, lineHeight: 28, color: '#1a1a1a' },
  tapHint: { fontSize: 12, color: '#00BCD4', marginTop: 16, textAlign: 'center', opacity: 0.7 },
  tapHintBack: { fontSize: 12, color: '#2e7d32', marginTop: 16, textAlign: 'center', opacity: 0.7 },
  progressBarWrap: { width: '100%', height: 6, backgroundColor: '#e0e0e0', borderRadius: 3, marginTop: 20, overflow: 'hidden' },
  progressBarFill: { height: '100%', backgroundColor: '#00BCD4', borderRadius: 3 },
  cardNav: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, width: '100%', paddingHorizontal: 8 },
  navBtn: { padding: 14, backgroundColor: '#00BCD4', borderRadius: 12 },
  navBtnDisabled: { opacity: 0.4 },
  navBtnText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  cardCounter: { fontSize: 15, color: '#666', fontWeight: '500', marginTop: 8 },
  empty: { textAlign: 'center', color: '#666', marginTop: 40 },
  // Footer
  footer: { backgroundColor: '#fff', padding: 16, borderTopWidth: 1, borderColor: '#eee' },
  footerLabel: { fontSize: 14, marginBottom: 8, color: '#666' },
  generateQuizBtn: { backgroundColor: '#2e7d32', padding: 14, borderRadius: 12, alignItems: 'center' },
  generateQuizBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  classroomPicker: { marginBottom: 12, maxHeight: 44 },
  classroomChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, backgroundColor: '#e0e0e0', marginRight: 8 },
  classroomChipActive: { backgroundColor: '#00BCD4' },
  classroomChipText: { fontSize: 14, color: '#333' },
  classroomChipTextActive: { color: '#fff' },
  postBtn: { backgroundColor: '#00BCD4', padding: 14, borderRadius: 10, alignItems: 'center' },
  postBtnDisabled: { opacity: 0.5 },
  postBtnText: { color: '#fff', fontWeight: '600' },
});
