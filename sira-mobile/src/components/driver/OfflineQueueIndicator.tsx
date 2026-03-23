/**
 * OfflineQueueIndicator — Shows pending offline actions count
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useOfflineStore } from '../../store/offline.store';
import { colors, typography, spacing, radii } from '../../theme';

export function OfflineQueueIndicator() {
  const { queueCount, syncStatus, isOnline } = useOfflineStore();

  if (isOnline && queueCount === 0) return null;

  const isSyncing = syncStatus === 'syncing';

  return (
    <View style={[styles.container, isSyncing ? styles.syncing : styles.offline]}>
      <Text style={[styles.text, isSyncing ? styles.textSyncing : styles.textOffline]}>
        {isSyncing
          ? `⟳  Syncing ${queueCount} item${queueCount !== 1 ? 's' : ''}...`
          : `📴 Offline — ${queueCount} action${queueCount !== 1 ? 's' : ''} queued`}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.sm,
    alignItems: 'center',
    borderWidth: 1,
    marginHorizontal: spacing.md,
    marginBottom: spacing.sm,
  },
  offline: {
    backgroundColor: colors.accentLight,
    borderColor: `${colors.accent}40`,
  },
  syncing: {
    backgroundColor: '#3D8EFF15',
    borderColor: '#3D8EFF40',
  },
  text: {
    ...typography.caption,
    fontWeight: '600',
  },
  textOffline: {
    color: colors.accent,
  },
  textSyncing: {
    color: colors.info,
  },
});
