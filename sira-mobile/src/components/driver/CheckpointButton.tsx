/**
 * CheckpointButton — THE core driver action button
 * Confirms a checkpoint, works fully offline.
 */
import React, { useState, useRef } from 'react';
import {
  View,
  TouchableOpacity,
  Text,
  StyleSheet,
  Animated,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { OfflineQueue } from '../../offline/queue';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import { colors, typography, spacing, radii } from '../../theme';

type ButtonState = 'idle' | 'confirming' | 'success' | 'error';

interface CheckpointButtonProps {
  shipmentId: number;
  organizationId: number;
  checkpointType?: string;
  location: { latitude: number; longitude: number } | null;
  onSuccess?: (eventId: string) => void;
  onError?: (error: string) => void;
}

const STATE_CONFIG: Record<ButtonState, { label: string; bg: string; text: string }> = {
  idle:       { label: '✓  CONFIRM CHECKPOINT', bg: colors.primary,    text: colors.white },
  confirming: { label: '   SAVING...',           bg: colors.primaryDim, text: colors.white },
  success:    { label: '✓  CHECKPOINT SAVED',   bg: colors.success,    text: colors.white },
  error:      { label: '✗  RETRY',              bg: colors.error,      text: colors.white },
};

export function CheckpointButton({
  shipmentId,
  organizationId,
  checkpointType = 'waypoint',
  location,
  onSuccess,
  onError,
}: CheckpointButtonProps) {
  const [state, setState] = useState<ButtonState>('idle');
  const { isOnline } = useNetworkStatus();
  const scale = useRef(new Animated.Value(1)).current;

  const handlePress = async () => {
    if (state === 'confirming') return;
    setState('confirming');
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);

    Animated.sequence([
      Animated.timing(scale, { toValue: 0.96, duration: 100, useNativeDriver: true }),
      Animated.timing(scale, { toValue: 1.0,  duration: 100, useNativeDriver: true }),
    ]).start();

    try {
      const eventId = OfflineQueue.push({
        type: 'CHECKPOINT_CONFIRMED',
        data: {
          shipment_id: shipmentId,
          organization_id: organizationId,
          checkpoint_type: checkpointType,
          latitude: location?.latitude ?? 0,
          longitude: location?.longitude ?? 0,
          offline_queued: !isOnline,
        },
      });

      setState('success');
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      onSuccess?.(eventId);
      setTimeout(() => setState('idle'), 2500);
    } catch (err: any) {
      setState('error');
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      onError?.(err?.message ?? 'Unknown error');
      setTimeout(() => setState('idle'), 2000);
    }
  };

  const cfg = STATE_CONFIG[state];

  return (
    <View style={styles.container}>
      {!isOnline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>
            📴 OFFLINE — Will sync when connected
          </Text>
        </View>
      )}
      <Animated.View style={{ transform: [{ scale }] }}>
        <TouchableOpacity
          style={[styles.button, { backgroundColor: cfg.bg }]}
          onPress={handlePress}
          activeOpacity={0.85}
          disabled={state === 'confirming'}
        >
          <Text style={[styles.buttonText, { color: cfg.text }]}>{cfg.label}</Text>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    paddingHorizontal: spacing.md,
  },
  offlineBanner: {
    backgroundColor: colors.accentLight,
    borderRadius: radii.sm,
    padding: spacing.sm + 2,
    marginBottom: spacing.sm,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: `${colors.accent}40`,
  },
  offlineText: {
    color: colors.accent,
    ...typography.caption,
    fontWeight: '600',
  },
  button: {
    height: 72,
    borderRadius: radii.lg,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  buttonText: {
    ...typography.buttonPrimary,
  },
});
