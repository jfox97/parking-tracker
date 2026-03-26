import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { logout, getCredentials } from '../services/auth';
import { unregisterDevice } from '../services/api';
import { scheduleLocalNotification } from '../services/notifications';

export default function SettingsScreen() {
  const [deviceInfo, setDeviceInfo] = useState<{
    deviceId: string | null;
  } | null>(null);
  const router = useRouter();

  // Load device info on mount
  useState(() => {
    const loadDeviceInfo = async () => {
      const { deviceId } = await getCredentials();
      setDeviceInfo({ deviceId });
    };
    loadDeviceInfo();
  });

  const handleTestNotification = async () => {
    try {
      await scheduleLocalNotification(
        'Test Notification',
        'Push notifications are working!',
        { type: 'test' }
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to send test notification');
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out? You will need an invitation code to sign back in.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: async () => {
            try {
              const { deviceId, authToken } = await getCredentials();
              if (deviceId && authToken) {
                // Try to unregister on server, but don't fail if it doesn't work
                try {
                  await unregisterDevice(deviceId, authToken);
                } catch (e) {
                  console.log('Failed to unregister on server:', e);
                }
              }
              await logout();
              router.replace('/onboarding');
            } catch (error) {
              Alert.alert('Error', 'Failed to sign out');
            }
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Device Info</Text>
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Device ID</Text>
          <Text style={styles.infoValue}>
            {deviceInfo?.deviceId
              ? `${deviceInfo.deviceId.slice(0, 8)}...`
              : 'Loading...'}
          </Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>
        <TouchableOpacity
          style={styles.button}
          onPress={handleTestNotification}
        >
          <Text style={styles.buttonText}>Send Test Notification</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Version</Text>
          <Text style={styles.infoValue}>1.0.0</Text>
        </View>
        <View style={styles.infoCard}>
          <Text style={styles.aboutText}>
            Parking Tracker monitors ski resort parking availability and sends
            you notifications when spots become available.
          </Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <TouchableOpacity
          style={[styles.button, styles.dangerButton]}
          onPress={handleLogout}
        >
          <Text style={styles.dangerButtonText}>Sign Out</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 16,
    color: '#1f2937',
    fontFamily: 'monospace',
  },
  aboutText: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
  },
  button: {
    backgroundColor: '#2563eb',
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  dangerButton: {
    backgroundColor: '#fee2e2',
  },
  dangerButtonText: {
    color: '#dc2626',
    fontSize: 16,
    fontWeight: '600',
  },
});
