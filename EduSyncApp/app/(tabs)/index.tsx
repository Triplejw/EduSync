import { useState } from 'react';
import { StyleSheet, Text, View, Button, ScrollView, ActivityIndicator, Alert } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import axios from 'axios';

// ✅ Your Laptop's USB Tethering IP
const API_URL = 'http://10.222.250.96:8000'; 

export default function App() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Idle');
  const [quiz, setQuiz] = useState('');

  const processDocument = async () => {
    try {
      // 1. Pick a file
      const result = await DocumentPicker.getDocumentAsync({
        type: ['image/*', 'application/pdf'],
      });

      if (result.canceled) return;

      const file = result.assets[0];
      setLoading(true);
      setStatus('Uploading & Extracting Text (OCR)...');

      // 2. Upload to Backend (OCR)
      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.mimeType || 'image/jpeg',
      } as any); // "as any" fixes TypeScript complaint

      const ocrResponse = await axios.post(`${API_URL}/extract-text`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const extractedText = ocrResponse.data.extracted_text;
      if (!extractedText) throw new Error("No text found in image");

      setStatus('Generating Quiz using Llama-3 (GPU)...');

      // 3. Send Text to LLM to make Quiz
      const quizResponse = await axios.post(`${API_URL}/generate-quiz`, {
        text: extractedText,
      });

      setQuiz(quizResponse.data.quiz);
      setStatus('Done!');
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Could not connect to EduSync Server. Check IP!');
      setStatus('Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>EduSync Teacher</Text>
      <Text style={styles.subtitle}>Edge AI Dashboard</Text>

      <View style={styles.card}>
        <Button title="Upload Lecture Slide" onPress={processDocument} disabled={loading} />
      </View>

      <View style={styles.statusContainer}>
        {loading && <ActivityIndicator size="large" color="#0000ff" />}
        <Text style={styles.statusText}>{status}</Text>
      </View>

      <ScrollView style={styles.resultContainer}>
        <Text style={styles.quizText}>{quiz}</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5', padding: 20, paddingTop: 60 },
  title: { fontSize: 28, fontWeight: 'bold', color: '#333', textAlign: 'center' },
  subtitle: { fontSize: 16, color: '#666', textAlign: 'center', marginBottom: 30 },
  card: { backgroundColor: 'white', padding: 20, borderRadius: 10, elevation: 3 },
  statusContainer: { marginTop: 20, alignItems: 'center' },
  statusText: { marginTop: 10, fontSize: 16, color: '#555' },
  resultContainer: { marginTop: 20, flex: 1 },
  quizText: { fontSize: 14, fontFamily: 'monospace', backgroundColor: '#e8e8e8', padding: 10, borderRadius: 5 },
});