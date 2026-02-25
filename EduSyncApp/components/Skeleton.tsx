import { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, ViewStyle, DimensionValue } from 'react-native';

interface SkeletonProps {
  width?: DimensionValue;
  height?: number;
  borderRadius?: number;
  style?: ViewStyle;
}

/**
 * Animated skeleton placeholder for loading states.
 * Displays a pulsing gray box that indicates content is loading.
 */
export function Skeleton({
  width = '100%',
  height = 20,
  borderRadius = 4,
  style,
}: SkeletonProps) {
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 0.7,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.3,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    );
    animation.start();
    return () => animation.stop();
  }, [opacity]);

  return (
    <Animated.View
      style={[
        styles.skeleton,
        {
          width,
          height,
          borderRadius,
          opacity,
        },
        style,
      ]}
    />
  );
}

interface SkeletonTextProps {
  lines?: number;
  lineHeight?: number;
  lastLineWidth?: DimensionValue;
  style?: ViewStyle;
}

/**
 * Multiple skeleton lines for text content.
 */
export function SkeletonText({
  lines = 3,
  lineHeight = 16,
  lastLineWidth = '60%',
  style,
}: SkeletonTextProps) {
  return (
    <View style={[styles.textContainer, style]}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={lineHeight}
          width={i === lines - 1 ? lastLineWidth : '100%'}
          style={i < lines - 1 ? { marginBottom: 8 } : undefined}
        />
      ))}
    </View>
  );
}

interface SkeletonCardProps {
  style?: ViewStyle;
}

/**
 * Skeleton for a typical list card item.
 */
export function SkeletonCard({ style }: SkeletonCardProps) {
  return (
    <View style={[styles.card, style]}>
      <View style={styles.cardHeader}>
        <Skeleton width={40} height={40} borderRadius={20} />
        <View style={styles.cardHeaderText}>
          <Skeleton width="60%" height={16} />
          <Skeleton width="40%" height={12} style={{ marginTop: 6 }} />
        </View>
      </View>
      <SkeletonText lines={2} style={{ marginTop: 12 }} />
    </View>
  );
}

interface SkeletonListProps {
  count?: number;
  style?: ViewStyle;
}

/**
 * A list of skeleton cards.
 */
export function SkeletonList({ count = 3, style }: SkeletonListProps) {
  return (
    <View style={style}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} style={i < count - 1 ? { marginBottom: 16 } : undefined} />
      ))}
    </View>
  );
}

interface SkeletonMaterialCardProps {
  style?: ViewStyle;
}

/**
 * Skeleton specifically for material list items.
 */
export function SkeletonMaterialCard({ style }: SkeletonMaterialCardProps) {
  return (
    <View style={[styles.materialCard, style]}>
      <View style={styles.materialIcon}>
        <Skeleton width={48} height={48} borderRadius={8} />
      </View>
      <View style={styles.materialContent}>
        <Skeleton width="70%" height={18} />
        <Skeleton width="90%" height={14} style={{ marginTop: 8 }} />
        <Skeleton width="40%" height={12} style={{ marginTop: 8 }} />
      </View>
    </View>
  );
}

interface SkeletonAssignmentCardProps {
  style?: ViewStyle;
}

/**
 * Skeleton specifically for assignment list items.
 */
export function SkeletonAssignmentCard({ style }: SkeletonAssignmentCardProps) {
  return (
    <View style={[styles.assignmentCard, style]}>
      <View style={styles.assignmentHeader}>
        <Skeleton width="60%" height={18} />
        <Skeleton width={60} height={24} borderRadius={12} />
      </View>
      <Skeleton width="80%" height={14} style={{ marginTop: 8 }} />
      <View style={styles.assignmentFooter}>
        <Skeleton width={80} height={12} />
        <Skeleton width={60} height={12} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  skeleton: {
    backgroundColor: '#e1e5eb',
  },
  textContainer: {
    width: '100%',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardHeaderText: {
    flex: 1,
    marginLeft: 12,
  },
  materialCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  materialIcon: {
    marginRight: 12,
  },
  materialContent: {
    flex: 1,
  },
  assignmentCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  assignmentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  assignmentFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
  },
});
