/**
 * EduSync API Configuration
 * - Web: localhost
 * - Physical device (Ethernet/USB): your laptop's IP (10.222.250.96)
 * - Android emulator: 10.0.2.2
 */
import { Platform } from 'react-native';

const BACKEND_IP = '10.222.250.96'; // Your laptop IP (enp5s0f3u1)
const BACKEND_PORT = 8000;

const getDefaultApiUrl = () => {
  if (Platform.OS === 'web') {
    return `http://localhost:${BACKEND_PORT}`;
  }
  // Physical device or emulator: use laptop IP (works when phone is on same network via Ethernet)
  return `http://${BACKEND_IP}:${BACKEND_PORT}`;
};

export const API_URL = (typeof process !== 'undefined' && (process as any).env?.EXPO_PUBLIC_API_URL) || getDefaultApiUrl();
