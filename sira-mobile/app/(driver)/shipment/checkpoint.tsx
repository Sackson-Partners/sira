/**
 * Checkpoint Confirmation Screen — Core Driver Action
 */
import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, Alert } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { CheckpointButton } from '../../../src/components/driver/CheckpointButton';
import { OfflineQueueIndicator } from '../../../src/components/driver/OfflineQueueIndicator';
import { useAuthStore } from '../../../src/store/auth.store';
import { getCurrentLocation } from '../../../src/hooks/useLocation';
import { colors, typography, spacing, radii } from '../../../src/theme';

export default function CheckpointScreen() {
  const { shipmentId, type } = useLocalSearchParams<{ shipmentId: string; type?: string }>();
  const { user } = useAuthStore();
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);

  useEffect(() => {
    getCurrentLocation().then(loc => {
      if (loc) {
        setLocation({
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
        });
      }
    });
  }, []);

  const handleSuccess = (eventId: string) => {
    Alert.alert(
      'Checkpoint Confirmed',
      `Checkpoint saved${location ? '' : ' (no GPS)'}\nEvent ID: ${eventId.slice(-8)}`,
      [{ text: 'OK', onPress: () => router.back() }],
    );
  };

  const checkpointType = type ?? 'waypoint';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.info}>
        <Text style={styles.title}>Confirm Checkpoint</Text>
        <Text style={styles.subtitle}>Shipment #{shipmentId}</Text>
        <Text style={styles.type}>Type: {checkpointType.replace('_', ' ').toUpperCase()}</Text>

        {location ? (
          <View style={styles.locationBox}>
            <Text style={styles.locationLabel}>📍 GPS Location Acquired</Text>
            <Text style={styles.locationCoords}>
              {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
            </Text>
          </View>
        ) : (
          <View style={styles.noLocationBox}>
            <Text style={styles.noLocationText}>⏳ Acquiring GPS location...</Text>
          </View>
        )}
      </View>

      <OfflineQueueIndicator />

      <CheckpointButton
        shipmentId={parseInt(shipmentId ?? '0', 10)}
        organizationId={user?.organization_id ?? 1}
        checkpointType={checkpointType}
        location={location}
        onSuccess={handleSuccess}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.md,
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  info: {
    gap: spacing.sm,
  },
  title: {
    ...typography.displayMedium,
    color: colors.textPrimary,
  },
  subtitle: {
    ...typography.bodyLarge,
    color: colors.textSecondary,
  },
  type: {
    ...typography.labelMedium,
    color: colors.accent,
  },
  locationBox: {
    backgroundColor: colors.successLight,
    borderRadius: radii.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: `${colors.success}40`,
    marginTop: spacing.sm,
  },
  locationLabel: {
    ...typography.labelMedium,
    color: colors.success,
  },
  locationCoords: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginTop: 2,
  },
  noLocationBox: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginTop: spacing.sm,
  },
  noLocationText: {
    ...typography.bodySmall,
    color: colors.textMuted,
  },
});
