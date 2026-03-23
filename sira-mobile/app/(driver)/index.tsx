/**
 * Driver Dashboard Screen
 */
import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { useAuthStore } from '../../src/store/auth.store';
import { useOfflineStore } from '../../src/store/offline.store';
import { OfflineQueueIndicator } from '../../src/components/driver/OfflineQueueIndicator';
import { StatusBadge } from '../../src/components/ui/StatusBadge';
import { colors, typography, spacing, radii } from '../../src/theme';

export default function DriverDashboard() {
  const { user } = useAuthStore();
  const { isOnline, queueCount } = useOfflineStore();

  const firstName = user?.full_name?.split(' ')[0] ?? user?.username ?? 'Driver';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.greeting}>Good morning, {firstName} 👋</Text>
        <Text style={styles.subGreeting}>You have 1 active shipment</Text>
        <View style={styles.statusRow}>
          <StatusBadge variant={isOnline ? 'online' : 'offline'} />
          {queueCount > 0 && (
            <StatusBadge variant="warning" label={`${queueCount} queued`} />
          )}
        </View>
      </View>

      {/* Offline Queue Indicator */}
      <OfflineQueueIndicator />

      {/* Active Shipment Card */}
      <TouchableOpacity
        style={styles.shipmentCard}
        onPress={() => router.push('/(driver)/shipment/1')}
        activeOpacity={0.85}
      >
        <View style={styles.cardHeader}>
          <Text style={styles.cardRef}>🚛 GH-2026-00092</Text>
          <StatusBadge variant="warning" label="IN TRANSIT" />
        </View>
        <Text style={styles.cardRoute}>Mine → Port of Tema</Text>
        <View style={styles.divider} />
        <View style={styles.cardMeta}>
          <Text style={styles.metaItem}>📍 N1 Highway, km 142</Text>
          <Text style={styles.metaItem}>🕒 ETA: 14:30 (2h 15m)</Text>
          <Text style={styles.metaItem}>⚠️ Risk: MEDIUM (52/100)</Text>
        </View>
        <View style={styles.cardCTA}>
          <Text style={styles.cardCTAText}>OPEN ACTIVE SHIPMENT →</Text>
        </View>
      </TouchableOpacity>

      {/* Recent Activity */}
      <Text style={styles.sectionTitle}>RECENT ACTIVITY</Text>
      <View style={styles.activityCard}>
        <Text style={styles.activityItem}>✓ Checkpoint: Mine Exit — 10:32</Text>
        <Text style={styles.activityItem}>✓ Start: Loading Bay — 08:15</Text>
      </View>
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
    gap: spacing.md,
  },
  header: {
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  greeting: {
    ...typography.displayMedium,
    color: colors.textPrimary,
  },
  subGreeting: {
    ...typography.bodyMedium,
    color: colors.textSecondary,
  },
  statusRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  shipmentCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardRef: {
    ...typography.labelLarge,
    color: colors.textPrimary,
  },
  cardRoute: {
    ...typography.bodyMedium,
    color: colors.textSecondary,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
  },
  cardMeta: {
    gap: spacing.xs,
  },
  metaItem: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  cardCTA: {
    backgroundColor: colors.primaryLight,
    borderRadius: radii.md,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  cardCTAText: {
    ...typography.buttonSecondary,
    color: colors.white,
  },
  sectionTitle: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 1.5,
    marginTop: spacing.sm,
  },
  activityCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.md,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  activityItem: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
});
