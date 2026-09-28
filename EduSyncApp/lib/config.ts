/**
 * EduSync API Configuration — Multi-Client LAN Setup
 *
 * How it works:
 *   1. EXPO_PUBLIC_API_URL env var takes priority (set at `npx expo start` time).
 *   2. Otherwise falls back to localhost for simulators and web development.
 *
 * Quick-switch networks:
 *   # Find your current LAN IP (WiFi preferred, Ethernet fallback):
 *   ./find_backend_ip.sh          # helper script in project root
 *
 *   # Option A — env var override (no code change needed):
 *   EXPO_PUBLIC_API_URL=http://<IP>:8000 npx expo start
 *
 * A physical iPhone must use EXPO_PUBLIC_API_URL with the Mac's current LAN IP.
 */
import { Platform } from 'react-native';

export const BACKEND_PORT = 8000;

const getDefaultApiUrl = () => {
  if (Platform.OS === 'web') {
    return `http://localhost:${BACKEND_PORT}`;
  }
  // Safe fallback for simulators. Physical devices must set EXPO_PUBLIC_API_URL.
  return `http://127.0.0.1:${BACKEND_PORT}`;
};

export const API_URL =
  (typeof process !== 'undefined' && (process as any).env?.EXPO_PUBLIC_API_URL) ||
  getDefaultApiUrl();
