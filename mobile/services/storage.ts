/**
 * AsyncStorage wrapper for persistent data storage.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  DEVICE_ID: 'parking_tracker_device_id',
  AUTH_TOKEN: 'parking_tracker_auth_token',
  FCM_TOKEN: 'parking_tracker_fcm_token',
  ONBOARDING_COMPLETE: 'parking_tracker_onboarding_complete',
};

export async function getDeviceId(): Promise<string | null> {
  return AsyncStorage.getItem(KEYS.DEVICE_ID);
}

export async function setDeviceId(deviceId: string): Promise<void> {
  await AsyncStorage.setItem(KEYS.DEVICE_ID, deviceId);
}

export async function getAuthToken(): Promise<string | null> {
  return AsyncStorage.getItem(KEYS.AUTH_TOKEN);
}

export async function setAuthToken(token: string): Promise<void> {
  await AsyncStorage.setItem(KEYS.AUTH_TOKEN, token);
}

export async function getFcmToken(): Promise<string | null> {
  return AsyncStorage.getItem(KEYS.FCM_TOKEN);
}

export async function setFcmToken(token: string): Promise<void> {
  await AsyncStorage.setItem(KEYS.FCM_TOKEN, token);
}

export async function isOnboardingComplete(): Promise<boolean> {
  const value = await AsyncStorage.getItem(KEYS.ONBOARDING_COMPLETE);
  return value === 'true';
}

export async function setOnboardingComplete(complete: boolean): Promise<void> {
  await AsyncStorage.setItem(KEYS.ONBOARDING_COMPLETE, complete ? 'true' : 'false');
}

export async function clearAllData(): Promise<void> {
  await AsyncStorage.multiRemove(Object.values(KEYS));
}
