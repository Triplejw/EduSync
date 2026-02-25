import { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const CONSENT_KEY = 'edusync_tracking_consent';

type ConsentStatus = 'pending' | 'granted' | 'denied';

interface PrivacyConsentProps {
  onConsentChange?: (granted: boolean) => void;
  forceShow?: boolean;
}

/**
 * Privacy consent modal for camera and scroll tracking.
 *
 * Shows a modal explaining what data is collected and why.
 * Consent is stored in AsyncStorage and persists across sessions.
 */
export function PrivacyConsent({ onConsentChange, forceShow = false }: PrivacyConsentProps) {
  const [visible, setVisible] = useState(false);
  const [consentStatus, setConsentStatus] = useState<ConsentStatus>('pending');

  useEffect(() => {
    checkConsent();
  }, []);

  useEffect(() => {
    if (forceShow && consentStatus !== 'pending') {
      setVisible(true);
    }
  }, [forceShow]);

  const checkConsent = async () => {
    try {
      const stored = await AsyncStorage.getItem(CONSENT_KEY);
      if (stored === 'granted') {
        setConsentStatus('granted');
        onConsentChange?.(true);
      } else if (stored === 'denied') {
        setConsentStatus('denied');
        onConsentChange?.(false);
      } else {
        // First time - show the modal
        setConsentStatus('pending');
        setVisible(true);
      }
    } catch (e) {
      // On error, show modal to be safe
      setVisible(true);
    }
  };

  const handleAccept = async () => {
    try {
      await AsyncStorage.setItem(CONSENT_KEY, 'granted');
      setConsentStatus('granted');
      onConsentChange?.(true);
      setVisible(false);
    } catch (e) {
      console.error('Failed to save consent:', e);
    }
  };

  const handleDecline = async () => {
    try {
      await AsyncStorage.setItem(CONSENT_KEY, 'denied');
      setConsentStatus('denied');
      onConsentChange?.(false);
      setVisible(false);
    } catch (e) {
      console.error('Failed to save consent:', e);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={() => {}}
    >
      <View style={styles.overlay}>
        <View style={styles.modal}>
          <ScrollView style={styles.scrollContent} showsVerticalScrollIndicator={false}>
            <Text style={styles.title}>Learning Analytics Consent</Text>

            <Text style={styles.intro}>
              EduSync uses advanced analytics to help improve your learning experience.
              Before we begin, we need your consent to collect certain data.
            </Text>

            <Text style={styles.sectionTitle}>What we collect:</Text>

            <View style={styles.item}>
              <Text style={styles.itemTitle}>Scroll Behavior</Text>
              <Text style={styles.itemDesc}>
                We analyze your scrolling patterns while reading materials to understand
                engagement levels. This helps identify which content is most effective.
              </Text>
            </View>

            <View style={styles.item}>
              <Text style={styles.itemTitle}>Camera (During Quizzes)</Text>
              <Text style={styles.itemDesc}>
                During quizzes, the front camera briefly captures head orientation to
                detect attention. Images are processed locally and never stored or transmitted.
              </Text>
            </View>

            <Text style={styles.sectionTitle}>How we use this data:</Text>
            <Text style={styles.paragraph}>
              {'\u2022'} Generate engagement scores to help teachers identify struggling students{'\n'}
              {'\u2022'} Research on learning analytics (anonymized){'\n'}
              {'\u2022'} Improve content delivery and quiz timing
            </Text>

            <Text style={styles.sectionTitle}>How your data stays local:</Text>
            <Text style={styles.paragraph}>
              {'\u2022'} Camera images are analyzed on the edge node and immediately discarded{'\n'}
              {'\u2022'} No biometric data is stored{'\n'}
              {'\u2022'} You can change your preference anytime in settings{'\n'}
              {'\u2022'} Declining will disable engagement tracking features
            </Text>
          </ScrollView>

          <View style={styles.buttons}>
            <TouchableOpacity
              style={[styles.btn, styles.declineBtn]}
              onPress={handleDecline}
            >
              <Text style={styles.declineBtnText}>Decline</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.btn, styles.acceptBtn]}
              onPress={handleAccept}
            >
              <Text style={styles.acceptBtnText}>Accept</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

/**
 * Hook to check current consent status.
 * Returns { hasConsent: boolean | null, loading: boolean, refresh: () => void }
 */
export function useTrackingConsent() {
  const [hasConsent, setHasConsent] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  const checkConsent = async () => {
    setLoading(true);
    try {
      const stored = await AsyncStorage.getItem(CONSENT_KEY);
      setHasConsent(stored === 'granted');
    } catch (e) {
      setHasConsent(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkConsent();
  }, []);

  return { hasConsent, loading, refresh: checkConsent };
}

/**
 * Reset consent (for settings screen).
 */
export async function resetTrackingConsent(): Promise<void> {
  await AsyncStorage.removeItem(CONSENT_KEY);
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modal: {
    backgroundColor: '#fff',
    borderRadius: 16,
    maxHeight: '85%',
    width: '100%',
    maxWidth: 400,
    overflow: 'hidden',
  },
  scrollContent: {
    padding: 24,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#00BCD4',
    marginBottom: 16,
    textAlign: 'center',
  },
  intro: {
    fontSize: 15,
    color: '#444',
    lineHeight: 22,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginTop: 12,
    marginBottom: 8,
  },
  item: {
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
  },
  itemTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#00BCD4',
    marginBottom: 4,
  },
  itemDesc: {
    fontSize: 13,
    color: '#555',
    lineHeight: 18,
  },
  paragraph: {
    fontSize: 14,
    color: '#555',
    lineHeight: 22,
    marginBottom: 8,
  },
  buttons: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  btn: {
    flex: 1,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  declineBtn: {
    borderRightWidth: 1,
    borderRightColor: '#eee',
  },
  acceptBtn: {
    backgroundColor: '#00BCD4',
  },
  declineBtnText: {
    fontSize: 16,
    color: '#666',
  },
  acceptBtnText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
});
