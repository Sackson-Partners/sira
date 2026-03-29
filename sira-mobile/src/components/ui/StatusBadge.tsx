import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../../theme/colors';

type BadgeVariant = 'online' | 'offline' | 'syncing' | 'risk-low' | 'risk-medium' | 'risk-high' | 'success' | 'warning' | 'error';

interface StatusBadgeProps {
  variant: BadgeVariant;
  label?: string;
}

const VARIANT_STYLES: Record<BadgeVariant, { bg: string; text: string; dot: string }> = {
  online:      { bg: colors.successLight,  text: colors.success,  dot: colors.success },
  offline:     { bg: colors.accentLight,   text: colors.accent,   dot: colors.accent },
  syncing:     { bg: colors.infoLight ?? '#3D8EFF20', text: colors.info, dot: colors.info },
  'risk-low':  { bg: colors.successLight,  text: colors.riskLow,  dot: colors.riskLow },
  'risk-medium':{ bg: colors.warningLight, text: colors.riskMedium, dot: colors.riskMedium },
  'risk-high': { bg: colors.errorLight,    text: colors.riskHigh, dot: colors.riskHigh },
  success:     { bg: colors.successLight,  text: colors.success,  dot: colors.success },
  warning:     { bg: colors.warningLight,  text: colors.warning,  dot: colors.warning },
  error:       { bg: colors.errorLight,    text: colors.error,    dot: colors.error },
};

const DEFAULT_LABELS: Record<BadgeVariant, string> = {
  online: 'Online',
  offline: 'Offline',
  syncing: 'Syncing...',
  'risk-low': 'Low Risk',
  'risk-medium': 'Medium Risk',
  'risk-high': 'High Risk',
  success: 'Success',
  warning: 'Warning',
  error: 'Error',
};

export function StatusBadge({ variant, label }: StatusBadgeProps) {
  const style = VARIANT_STYLES[variant];
  const displayLabel = label ?? DEFAULT_LABELS[variant];

  return (
    <View style={[styles.badge, { backgroundColor: style.bg }]}>
      <View style={[styles.dot, { backgroundColor: style.dot }]} />
      <Text style={[styles.text, { color: style.text }]}>{displayLabel}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 100,
    gap: 6,
    alignSelf: 'flex-start',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
});
