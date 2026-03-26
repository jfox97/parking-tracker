import { useEffect, useState } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { isDeviceRegistered } from '../services/auth';
import {
  setupTokenRefreshListener,
  setupNotificationReceivedListener,
  setupNotificationResponseListener,
} from '../services/notifications';

export default function RootLayout() {
  const [isLoading, setIsLoading] = useState(true);
  const [isRegistered, setIsRegistered] = useState(false);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    // Check if device is registered
    const checkRegistration = async () => {
      const registered = await isDeviceRegistered();
      setIsRegistered(registered);
      setIsLoading(false);
    };

    checkRegistration();

    // Set up notification listeners
    const cleanupTokenRefresh = setupTokenRefreshListener();
    const cleanupNotificationReceived = setupNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification);
    });
    const cleanupNotificationResponse = setupNotificationResponseListener((response) => {
      console.log('Notification tapped:', response);
      // Handle deep link from notification
      const data = response.notification.request.content.data;
      if (data?.type === 'parking_alert') {
        // Navigate to subscriptions
        router.push('/');
      }
    });

    return () => {
      cleanupTokenRefresh();
      cleanupNotificationReceived();
      cleanupNotificationResponse();
    };
  }, []);

  useEffect(() => {
    if (isLoading) return;

    const handleNavigation = async () => {
      const inOnboarding = segments[0] === 'onboarding';

      // Re-check registration status when navigating
      const registered = await isDeviceRegistered();

      if (!registered && !inOnboarding) {
        // Redirect to onboarding if not registered
        router.replace('/onboarding');
      } else if (registered && inOnboarding) {
        // Redirect to home if already registered
        router.replace('/');
      }

      // Update state if changed
      if (registered !== isRegistered) {
        setIsRegistered(registered);
      }
    };

    handleNavigation();
  }, [isLoading, segments]);

  if (isLoading) {
    return null; // Or a loading screen
  }

  return (
    <>
      <StatusBar style="auto" />
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: '#2563eb',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
          },
        }}
      >
        <Stack.Screen
          name="index"
          options={{
            title: 'Parking Tracker',
          }}
        />
        <Stack.Screen
          name="subscribe"
          options={{
            title: 'New Alert',
            presentation: 'modal',
          }}
        />
        <Stack.Screen
          name="settings"
          options={{
            title: 'Settings',
          }}
        />
        <Stack.Screen
          name="onboarding/index"
          options={{
            title: 'Welcome',
            headerShown: false,
          }}
        />
      </Stack>
    </>
  );
}
