import { Tabs } from 'expo-router';
import { colors } from '../../src/theme';

export default function DriverLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          height: 72,
        },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.textPrimary,
        headerTitleStyle: { fontWeight: '700', color: colors.textPrimary },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: 'Dashboard', tabBarIcon: () => null }}
      />
      <Tabs.Screen
        name="shipment/[id]"
        options={{ title: 'Shipment', tabBarIcon: () => null }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: 'History', tabBarIcon: () => null }}
      />
    </Tabs>
  );
}
