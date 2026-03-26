/**
 * API client for the parking tracker backend.
 */

// Update this to your actual API URL
const API_BASE_URL = 'https://parking.foxjason.com/api';

interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  error?: string;
  data?: T;
}

interface Resort {
  name: string;
  display_name: string;
}

interface Subscription {
  resort: string;
  date: string;
  status: string;
  notification_type: string;
  unsubscribe_token: string;
}

interface RegisterDeviceResponse {
  success: boolean;
  message: string;
  auth_token: string;
  device_id: string;
}

interface SubscribeResponse {
  success: boolean;
  message: string;
  unsubscribe_token: string;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || `API error: ${response.status}`);
  }

  return data;
}

/**
 * Get list of available resorts.
 */
export async function getResorts(): Promise<Resort[]> {
  const response = await fetchApi<{ resorts: Resort[] }>('/resorts');
  return response.resorts;
}

/**
 * Verify an invitation code.
 */
export async function verifyInvitationCode(code: string): Promise<boolean> {
  try {
    const response = await fetchApi<{ valid: boolean }>('/verify-code', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
    return response.valid;
  } catch {
    return false;
  }
}

/**
 * Register a new device.
 */
export async function registerDevice(
  deviceId: string,
  fcmToken: string,
  platform: string,
  invitationCode: string
): Promise<RegisterDeviceResponse> {
  return fetchApi<RegisterDeviceResponse>('/devices/register', {
    method: 'POST',
    body: JSON.stringify({
      device_id: deviceId,
      fcm_token: fcmToken,
      platform,
      invitation_code: invitationCode,
    }),
  });
}

/**
 * Refresh FCM token for a device.
 */
export async function refreshFcmToken(
  deviceId: string,
  fcmToken: string,
  authToken: string
): Promise<void> {
  await fetchApi('/devices/refresh-token', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      device_id: deviceId,
      fcm_token: fcmToken,
    }),
  });
}

/**
 * Get subscriptions for a device.
 */
export async function getDeviceSubscriptions(
  deviceId: string,
  authToken: string
): Promise<Subscription[]> {
  const response = await fetchApi<{ subscriptions: Subscription[] }>(
    `/devices/${deviceId}/subscriptions`,
    {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    }
  );
  return response.subscriptions;
}

/**
 * Subscribe a device to parking alerts.
 */
export async function subscribeDevice(
  deviceId: string,
  resort: string,
  date: string,
  authToken: string,
  notificationType: 'push' | 'sms' | 'both' = 'push',
  phoneNumber?: string
): Promise<SubscribeResponse> {
  return fetchApi<SubscribeResponse>(`/devices/${deviceId}/subscribe`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      resort,
      date,
      notification_type: notificationType,
      phone_number: phoneNumber,
    }),
  });
}

/**
 * Unsubscribe from a specific alert.
 */
export async function unsubscribeDevice(token: string): Promise<void> {
  await fetchApi('/devices/unsubscribe', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
}

/**
 * Unregister a device completely.
 */
export async function unregisterDevice(
  deviceId: string,
  authToken: string
): Promise<void> {
  await fetchApi(`/devices/${deviceId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });
}
