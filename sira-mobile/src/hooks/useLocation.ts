import { useEffect } from 'react';
import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import { OfflineQueue } from '../offline/queue';

const LOCATION_TASK = 'SIRA_BACKGROUND_LOCATION';
const LOCATION_INTERVAL_MS = 30_000; // 30 seconds

// Background task must be registered at module level
TaskManager.defineTask(LOCATION_TASK, async ({ data, error }) => {
  if (error) {
    console.warn('[SIRA Location]', error.message);
    return;
  }
  const { locations } = data as { locations: Location.LocationObject[] };
  const loc = locations[0];
  if (!loc) return;

  OfflineQueue.push({
    type: 'DRIVER_LOCATION',
    data: {
      latitude: loc.coords.latitude,
      longitude: loc.coords.longitude,
      speed_kmh: loc.coords.speed != null ? loc.coords.speed * 3.6 : undefined,
      accuracy_m: loc.coords.accuracy ?? undefined,
      timestamp: new Date(loc.timestamp).toISOString(),
    },
  });
});

export function useBackgroundLocation(shipmentId: number | null) {
  useEffect(() => {
    if (!shipmentId) return;

    let started = false;

    (async () => {
      const { status } = await Location.requestBackgroundPermissionsAsync();
      if (status !== 'granted') return;

      await Location.startLocationUpdatesAsync(LOCATION_TASK, {
        accuracy: Location.Accuracy.High,
        timeInterval: LOCATION_INTERVAL_MS,
        distanceInterval: 100, // Only update if moved ≥100m
        showsBackgroundLocationIndicator: true,
        foregroundService: {
          notificationTitle: 'SIRA Tracking Active',
          notificationBody: `Tracking shipment #${shipmentId}`,
          notificationColor: '#0A1F44',
        },
      });
      started = true;
    })();

    return () => {
      if (started) {
        Location.stopLocationUpdatesAsync(LOCATION_TASK).catch(() => {});
      }
    };
  }, [shipmentId]);
}

/**
 * One-shot current location.
 */
export async function getCurrentLocation(): Promise<Location.LocationObject | null> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status !== 'granted') return null;

  return Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.High,
  });
}
