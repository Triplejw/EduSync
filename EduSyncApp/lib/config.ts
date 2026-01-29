/**
 * EduSync API Configuration
 * Change BACKEND_IP to your backend server IP when running on device/emulator.
 * - Web: use localhost
 * - Android emulator: use 10.0.2.2
 * - iOS simulator: use localhost
 * - Physical device: use your computer's IP (e.g. 192.168.1.100)
 */
import { Platform } from 'react-native';

const BACKEND_IP = 'localhost'; // Change to your IP for mobile (e.g. '192.168.1.100')
const BACKEND_PORT = 8000;

const getDefaultApiUrl = () => {
  if (Platform.OS === 'web') {
    return `http://localhost:${BACKEND_PORT}`;
  }
  if (Platform.OS === 'android') {
    return `http://10.0.2.2:${BACKEND_PORT}`; // Android emulator
  }
  return `http://${BACKEND_IP}:${BACKEND_PORT}`;
};

export const API_URL = (typeof process !== 'undefined' && (process as any).env?.EXPO_PUBLIC_API_URL) || getDefaultApiUrl();
