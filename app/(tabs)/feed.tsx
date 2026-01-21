import React from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Dummy Data for UI Development
const COURSES = [
  { id: '1', title: 'Digital Signal Processing', code: 'ECE301', teacher: 'Dr. Sharma', color: '#1E88E5' },
  { id: '2', title: 'VLSI Design', code: 'ECE302', teacher: 'Prof. Anitha', color: '#43A047' },
  { id: '3', title: 'Control Systems', code: 'ECE303', teacher: 'Dr. Raj', color: '#E53935' },
];

export default function FeedScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Google Classroom</Text>
        <TouchableOpacity style={styles.addBtn}>
          <Ionicons name="add" size={24} color="#333" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={COURSES}
        keyExtractor={item => item.id}
        contentContainerStyle={{ padding: 16, gap: 16 }}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card}>
            <View style={[styles.cardBanner, { backgroundColor: item.color }]}>
              <View style={styles.bannerContent}>
                <Text style={styles.courseTitle}>{item.title}</Text>
                <Text style={styles.courseCode}>{item.code}</Text>
              </View>
              <Text style={styles.teacherName}>{item.teacher}</Text>
            </View>
            <View style={styles.cardFooter}>
              <Text style={styles.assignmentText}>2 Assignments Due</Text>
            </View>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', paddingTop: 50 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, marginBottom: 10, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#333' },
  addBtn: { padding: 8, backgroundColor: '#f2f2f2', borderRadius: 20 },
  
  // Card Styles (Google Classroom Look)
  card: { backgroundColor: '#fff', borderRadius: 12, borderWidth: 1, borderColor: '#e0e0e0', overflow: 'hidden', elevation: 2 },
  cardBanner: { height: 100, padding: 16, justifyContent: 'space-between' },
  bannerContent: {},
  courseTitle: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  courseCode: { fontSize: 14, color: 'rgba(255,255,255,0.9)', marginTop: 4 },
  teacherName: { fontSize: 12, color: '#fff', fontWeight: '600' },
  cardFooter: { padding: 16, backgroundColor: '#fff' },
  assignmentText: { color: '#666', fontSize: 14 },
});
