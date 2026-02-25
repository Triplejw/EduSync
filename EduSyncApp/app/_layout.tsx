import { View, StyleSheet } from 'react-native';
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useCallback } from 'react';
import { useRouter } from 'expo-router';
import 'react-native-reanimated';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { IntroProvider, useIntro } from '@/context/IntroContext';
import IntroScreen from './intro';

SplashScreen.preventAutoHideAsync();

function RootLayoutNav() {
  const colorScheme = useColorScheme();
  const { loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      SplashScreen.hideAsync();
    }
  }, [loading]);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="register" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="classroom/[id]" options={{ title: 'Classroom' }} />
        <Stack.Screen name="material/[id]" options={{ title: 'Material' }} />
        <Stack.Screen name="assignment/[id]" options={{ title: 'Assignment' }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}

function IntroGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { showIntro, hideIntro } = useIntro();

  const handleIntroDone = useCallback(() => {
    hideIntro();
    router.replace('/');
  }, [hideIntro, router]);

  useEffect(() => {
    SplashScreen.hideAsync();
  }, []);

  // Always mount the Stack so expo-router's REPLACE to "index" is handled.
  // Show intro on cold start and when triggered (e.g., logout).
  return (
    <View style={styles.gate}>
      {children}
      {showIntro && (
        <View style={styles.introOverlay} pointerEvents="box-none">
          <IntroScreen onDone={handleIntroDone} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  gate: { flex: 1 },
  introOverlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 9999,
  },
});

export default function RootLayout() {
  return (
    <AuthProvider>
      <IntroProvider>
        <IntroGate>
          <RootLayoutNav />
        </IntroGate>
      </IntroProvider>
    </AuthProvider>
  );
}
