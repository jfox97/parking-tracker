/**
 * Device authentication and registration service.
 */

import { Platform } from 'react-native';
import { registerDevice as apiRegisterDevice } from './api';
import { registerForPushNotifications } from './notifications';
import {
  getAuthToken,
  getDeviceId,
  setAuthToken,
  setDeviceId,
  setOnboardingComplete,
  clearAllData,
} from './storage';

/**
 * Generate a unique device ID using UUID v4.
 */
export function generateDeviceId(): string {
  // Simple UUID v4 generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get the current platform name.
 */
export function getPlatform(): 'android' | 'ios' | 'web' {
  if (Platform.OS === 'android') return 'android';
  if (Platform.OS === 'ios') return 'ios';
  return 'web';
}

/**
 * Check if the device is registered.
 */
export async function isDeviceRegistered(): Promise<boolean> {
  const deviceId = await getDeviceId();
  const authToken = await getAuthToken();
  return !!(deviceId && authToken);
}

/**
 * Register a new device with an invitation code.
 * Returns true if registration was successful.
 */
export async function registerDeviceWithCode(
  invitationCode: string
): Promise<{ success: boolean; error?: string }> {
  try {
    // Generate a new device ID
    const deviceId = generateDeviceId();

    // Register for push notifications and get FCM token
    const fcmToken = await registerForPushNotifications();

    if (!fcmToken) {
      return {
        success: false,
        error: 'Could not get push notification token. Please allow notifications.',
      };
    }

    // Get platform
    const platform = getPlatform();

    // Register with the backend
    const response = await apiRegisterDevice(
      deviceId,
      fcmToken,
      platform,
      invitationCode
    );

    if (response.success && response.auth_token) {
      // Save credentials locally
      await setDeviceId(deviceId);
      await setAuthToken(response.auth_token);
      await setOnboardingComplete(true);

      return { success: true };
    }

    return {
      success: false,
      error: response.message || 'Registration failed',
    };
  } catch (error) {
    console.error('Registration error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Registration failed',
    };
  }
}

/**
 * Get the current auth credentials.
 */
export async function getCredentials(): Promise<{
  deviceId: string | null;
  authToken: string | null;
}> {
  const deviceId = await getDeviceId();
  const authToken = await getAuthToken();
  return { deviceId, authToken };
}

/**
 * Log out and clear all stored data.
 */
export async function logout(): Promise<void> {
  await clearAllData();
}
