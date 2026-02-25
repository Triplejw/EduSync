/**
 * EduSync API Configuration — Multi-Client LAN Setup
 *
 * How it works:
 *   1. EXPO_PUBLIC_API_URL env var takes priority (set at `npx expo start` time).
 *   2. Otherwise falls back to the BACKEND_IP constant below.
 *
 * Quick-switch networks:
 *   # Find your current LAN IP (WiFi preferred, Ethernet fallback):
 *   ./find_backend_ip.sh          # helper script in project root
 *
 *   # Option A — env var override (no code change needed):
 *   EXPO_PUBLIC_API_URL=http://<IP>:8000 npx expo start
 *
 *   # Option B — edit the constant below and restart Expo.
 *
 * Network interfaces:
 *   - wlp4s0       (WiFi, preferred for multi-client data collection)
 *   - enp5s0f3u1   (Ethernet / USB tether, fallback)
 *   - Android emulator: use 10.0.2.2
 */
import { Platform } from 'react-native';

// >>> UPDATE THIS to your machine's current LAN IP <<<
// Run: ./find_backend_ip.sh   or   ip -4 addr show wlp4s0
export const BACKEND_IP = '172.20.10.2'; // iPhone hotspot network
export const BACKEND_PORT = 8000;

const getDefaultApiUrl = () => {
  if (Platform.OS === 'web') {
    return `http://localhost:${BACKEND_PORT}`;
  }
  // Physical device: use the LAN IP so all clients on the same WiFi can reach the backend
  return `http://${BACKEND_IP}:${BACKEND_PORT}`;
};

export const API_URL =
  (typeof process !== 'undefined' && (process as any).env?.EXPO_PUBLIC_API_URL) ||
  getDefaultApiUrl();
