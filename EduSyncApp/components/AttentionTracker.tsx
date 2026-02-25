import { useEffect, useRef, useState, useCallback } from 'react';
import { StyleSheet, View, Text, Animated, Alert, Linking, Platform } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { submitAttention } from '@/lib/api';
import { PrivacyConsent, useTrackingConsent } from './PrivacyConsent';

const CAPTURE_INTERVAL_MS = 2000; // Every 2 seconds

type AttentionTrackerProps = {
  studentId: string;
  assignmentId?: number;
  onAttentionChange?: (score: number, isAttentive: boolean) => void;
  showIndicator?: boolean;
};

/**
 * Attention tracking component using camera-based head pose estimation.
 *
 * - Shows PrivacyConsent modal if user hasn't responded yet
 * - Requests camera permission with explanation
 * - Captures front camera every 2s and sends to backend
 * - Optional visual indicator showing attention status
 */
export function AttentionTracker({
  studentId,
  assignmentId,
  onAttentionChange,
  showIndicator = false,
}: AttentionTrackerProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraReady, setCameraReady] = useState(false);
  const [attentionScore, setAttentionScore] = useState<number | null>(null);
  const [isAttentive, setIsAttentive] = useState(true);
  const { hasConsent, loading: consentLoading, refresh: refreshConsent } = useTrackingConsent();
  const [permissionRequested, setPermissionRequested] = useState(false);

  const cameraRef = useRef<CameraView>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // Pulse animation for the indicator
  useEffect(() => {
    if (!showIndicator || isAttentive) return;

    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, [showIndicator, isAttentive, pulseAnim]);

  const captureAndSend = useCallback(async () => {
    if (!cameraRef.current) return;

    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.3,
        base64: true,
      });

      if (photo?.base64) {
        const result = await submitAttention(
          photo.base64,
          studentId,
          Date.now(),
          assignmentId
        );

        // Handle response with attention score
        if (result && typeof result.attention_score === 'number') {
          const score = result.attention_score;
          setAttentionScore(score);
          const attentive = score >= 50;
          setIsAttentive(attentive);
          onAttentionChange?.(score, attentive);
        }
      }
    } catch {
      // Silently fail - don't disrupt user experience
    }
  }, [studentId, assignmentId, onAttentionChange]);

  // Request camera permission once consent is granted
  useEffect(() => {
    if (consentLoading || !hasConsent) return;
    if (!permission) return;
    if (permission.granted) return; // Already granted
    if (permissionRequested) return; // Already asked

    setPermissionRequested(true);

    // Show an alert explaining why we need camera before the OS prompt
    Alert.alert(
      'Camera Access Needed',
      'EduSync uses the front camera during quizzes to track attention and help improve your learning experience. No images are stored.',
      [
        {
          text: 'Not Now',
          style: 'cancel',
        },
        {
          text: 'Allow',
          onPress: async () => {
            const result = await requestPermission();
            if (!result.granted && result.canAskAgain === false) {
              // Permission permanently denied — guide user to settings
              Alert.alert(
                'Camera Permission Required',
                'Camera access was denied. Please enable it in your device settings to use attention tracking.',
                [
                  { text: 'Cancel', style: 'cancel' },
                  {
                    text: 'Open Settings',
                    onPress: () => {
                      if (Platform.OS === 'ios') {
                        Linking.openURL('app-settings:');
                      } else {
                        Linking.openSettings();
                      }
                    },
                  },
                ]
              );
            }
          },
        },
      ]
    );
  }, [consentLoading, hasConsent, permission, permissionRequested, requestPermission]);

  // Start capture interval when everything is ready
  useEffect(() => {
    if (consentLoading || !hasConsent) return;
    if (!permission?.granted || !cameraReady) return;

    intervalRef.current = setInterval(captureAndSend, CAPTURE_INTERVAL_MS);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [permission?.granted, cameraReady, captureAndSend, hasConsent, consentLoading]);

  // Show PrivacyConsent modal if user hasn't consented yet
  // This is the actual modal that lets the user accept/decline
  if (!consentLoading && hasConsent === false) {
    return (
      <PrivacyConsent
        onConsentChange={(granted) => {
          // Refresh the hook state after the modal is dismissed
          refreshConsent();
        }}
      />
    );
  }

  // Don't render camera until consent + permission are ready
  if (consentLoading || !hasConsent) return null;
  if (!permission || !permission.granted) return null;

  return (
    <>
      {/* Camera preview — needs reasonable size to capture frames, hidden off-screen */}
      <View style={styles.hiddenCamera} pointerEvents="none">
        <CameraView
          ref={cameraRef}
          style={styles.camera}
          facing="front"
          onCameraReady={() => setCameraReady(true)}
        />
      </View>

      {/* Optional attention indicator */}
      {showIndicator && attentionScore !== null && (
        <Animated.View
          style={[
            styles.indicator,
            isAttentive ? styles.indicatorAttentive : styles.indicatorDistracted,
            { transform: [{ scale: isAttentive ? 1 : pulseAnim }] },
          ]}
        >
          <Text style={styles.indicatorText}>
            {isAttentive ? 'Focused' : 'Look here'}
          </Text>
        </Animated.View>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  hiddenCamera: {
    position: 'absolute',
    width: 150,
    height: 150,
    overflow: 'hidden',
    opacity: 0.01,
    top: -150,
    left: 0,
  },
  camera: {
    width: 150,
    height: 150,
  },
  indicator: {
    position: 'absolute',
    top: 16,
    right: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    zIndex: 100,
  },
  indicatorAttentive: {
    backgroundColor: 'rgba(34, 197, 94, 0.9)',
  },
  indicatorDistracted: {
    backgroundColor: 'rgba(239, 68, 68, 0.9)',
  },
  indicatorText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
});
