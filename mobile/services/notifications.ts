/**
 * Push notification setup and handling using Expo Notifications.
 */

import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { refreshFcmToken } from './api';
import { getAuthToken, getDeviceId, getFcmToken, setFcmToken } from './storage';

// Configure notification handler for foreground notifications
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

/**
 * Register for push notifications and get the FCM token.
 * Returns the token if successful, null otherwise.
 */
export async function registerForPushNotifications(): Promise<string | null> {
  // Push notifications only work on physical devices
  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }

  // Check existing permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  // Request permissions if not already granted
  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Push notification permission denied');
    return null;
  }

  // Set up Android notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('parking_alerts', {
      name: 'Parking Alerts',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
      sound: 'default',
    });
  }

  try {
    // Get the native FCM token (not Expo push token) since backend uses FCM directly
    const tokenData = await Notifications.getDevicePushTokenAsync();

    const token = tokenData.data;
    console.log('FCM token:', token);

    // Save the token locally
    await setFcmToken(token);

    return token;
  } catch (error) {
    console.error('Error getting push token:', error);
    return null;
  }
}

/**
 * Set up listener for token refresh events.
 * Call this on app startup to ensure we always have a valid token.
 */
export function setupTokenRefreshListener(): () => void {
  const subscription = Notifications.addPushTokenListener(async (token) => {
    console.log('Push token refreshed:', token.data);

    const newToken = token.data;
    const previousToken = await getFcmToken();

    // Only update if the token changed
    if (newToken !== previousToken) {
      await setFcmToken(newToken);

      // Try to refresh token on the server
      const deviceId = await getDeviceId();
      const authToken = await getAuthToken();

      if (deviceId && authToken) {
        try {
          await refreshFcmToken(deviceId, newToken, authToken);
          console.log('Token refreshed on server');
        } catch (error) {
          console.error('Failed to refresh token on server:', error);
        }
      }
    }
  });

  return () => subscription.remove();
}

/**
 * Set up listener for notification received events.
 */
export function setupNotificationReceivedListener(
  callback: (notification: Notifications.Notification) => void
): () => void {
  const subscription = Notifications.addNotificationReceivedListener(callback);
  return () => subscription.remove();
}

/**
 * Set up listener for notification response (tap) events.
 */
export function setupNotificationResponseListener(
  callback: (response: Notifications.NotificationResponse) => void
): () => void {
  const subscription = Notifications.addNotificationResponseReceivedListener(callback);
  return () => subscription.remove();
}

/**
 * Get the last notification response (for handling deep links from notifications).
 */
export async function getLastNotificationResponse(): Promise<Notifications.NotificationResponse | null> {
  return Notifications.getLastNotificationResponseAsync();
}

/**
 * Schedule a local notification (for testing).
 */
export async function scheduleLocalNotification(
  title: string,
  body: string,
  data?: Record<string, unknown>
): Promise<string> {
  return Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data,
      sound: 'default',
    },
    trigger: null, // Immediate
  });
}

/**
 * Cancel all scheduled notifications.
 */
export async function cancelAllNotifications(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}

/**
 * Get the badge count.
 */
export async function getBadgeCount(): Promise<number> {
  return Notifications.getBadgeCountAsync();
}

/**
 * Set the badge count.
 */
export async function setBadgeCount(count: number): Promise<void> {
  await Notifications.setBadgeCountAsync(count);
}
