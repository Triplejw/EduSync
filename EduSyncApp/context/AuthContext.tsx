import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as api from '@/lib/api';

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: 'teacher' | 'student';
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string, role: 'teacher' | 'student') => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY_USER = '@edusync_user';
const STORAGE_KEY_TOKEN = '@edusync_access_token';

async function getStoredAuth(): Promise<{ user: User; accessToken: string } | null> {
  try {
    const userStr = await AsyncStorage.getItem(STORAGE_KEY_USER);
    const token = await AsyncStorage.getItem(STORAGE_KEY_TOKEN);
    if (userStr && token) {
      return { user: JSON.parse(userStr) as User, accessToken: token };
    }
  } catch (_) {}
  return null;
}

async function setStoredAuth(user: User | null, accessToken: string | null): Promise<void> {
  try {
    if (user && accessToken) {
      await AsyncStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
      await AsyncStorage.setItem(STORAGE_KEY_TOKEN, accessToken);
    } else {
      await AsyncStorage.removeItem(STORAGE_KEY_USER);
      await AsyncStorage.removeItem(STORAGE_KEY_TOKEN);
    }
  } catch (_) {}
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const persistAuth = useCallback(async (u: User | null, token: string | null) => {
    await setStoredAuth(u, token);
  }, []);

  const loadStoredAuth = useCallback(async () => {
    try {
      const auth = await getStoredAuth();
      if (auth) {
        setUser(auth.user);
        api.setAuthHeader(auth.accessToken);
      }
    } catch (e) {
      console.warn('Failed to load stored auth', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStoredAuth();
  }, [loadStoredAuth]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.login(email, password);
    const u: User = {
      id: data.user.id,
      email: data.user.email,
      full_name: data.user.full_name,
      role: data.user.role,
    };
    const token = data.access_token;
    setUser(u);
    api.setAuthHeader(token);
    await persistAuth(u, token);
  }, [persistAuth]);

  const register = useCallback(async (email: string, password: string, full_name: string, role: 'teacher' | 'student') => {
    const data = await api.register(email, password, full_name, role);
    const u: User = {
      id: data.user.id,
      email: data.user.email,
      full_name: data.user.full_name,
      role: data.user.role,
    };
    const token = data.access_token;
    setUser(u);
    api.setAuthHeader(token);
    await persistAuth(u, token);
  }, [persistAuth]);

  const logout = useCallback(async () => {
    setUser(null);
    api.clearAuthHeader();
    await persistAuth(null, null);
  }, [persistAuth]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
