import { useRef, useCallback, useEffect } from 'react';
import { NativeSyntheticEvent, NativeScrollEvent } from 'react-native';

/**
 * Hook to track scroll behavior and sample scroll delta at 1Hz.
 * Used for engagement analytics - tracks how users scroll through materials.
 *
 * Usage:
 * const { onScroll, getScrollSignal, reset, pushDelta } = useScrollTracker();
 * <ScrollView onScroll={onScroll} scrollEventThrottle={100}>
 * For PDF WebView scroll, use onMessage and pushDelta(pixelsPerSecond).
 *
 * On unmount or when leaving the screen:
 * const signal = getScrollSignal();
 * await submitAnalytics(materialId, signal);
 */
export function useScrollTracker() {
  const lastScrollY = useRef(0);
  const lastSampleTime = useRef(Date.now());
  const scrollSignal = useRef<number[]>([]);
  const accumulatedDelta = useRef(0);

  // Sample at 1Hz (every 1000ms)
  const SAMPLE_INTERVAL_MS = 1000;

  const onScroll = useCallback((event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const currentY = event.nativeEvent.contentOffset.y;
    const now = Date.now();

    // Calculate delta (absolute value - we care about activity, not direction)
    const delta = Math.abs(currentY - lastScrollY.current);
    accumulatedDelta.current += delta;
    lastScrollY.current = currentY;

    // Check if it's time to sample (1Hz)
    const elapsed = now - lastSampleTime.current;
    if (elapsed >= SAMPLE_INTERVAL_MS) {
      // Calculate pixels per second
      const pixelsPerSecond = Math.round((accumulatedDelta.current / elapsed) * 1000);
      scrollSignal.current.push(pixelsPerSecond);

      // Reset for next sample
      accumulatedDelta.current = 0;
      lastSampleTime.current = now;
    }
  }, []);

  const getScrollSignal = useCallback(() => {
    // Flush any remaining accumulated delta as final sample
    const now = Date.now();
    const elapsed = now - lastSampleTime.current;
    if (elapsed > 100 && accumulatedDelta.current > 0) {
      const pixelsPerSecond = Math.round((accumulatedDelta.current / elapsed) * 1000);
      scrollSignal.current.push(pixelsPerSecond);
    }
    return [...scrollSignal.current];
  }, []);

  const reset = useCallback(() => {
    scrollSignal.current = [];
    accumulatedDelta.current = 0;
    lastSampleTime.current = Date.now();
    lastScrollY.current = 0;
  }, []);

  /** Push one 1 Hz sample from an external source (e.g. PDF WebView scroll). */
  const pushDelta = useCallback((pixelsPerSecond: number) => {
    scrollSignal.current.push(Math.round(pixelsPerSecond));
    lastSampleTime.current = Date.now();
  }, []);

  return {
    onScroll,
    getScrollSignal,
    reset,
    pushDelta,
  };
}
