import { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Calendar, DateData } from 'react-native-calendars';
import { getResorts, subscribeDevice } from '../services/api';
import { getCredentials } from '../services/auth';

interface Resort {
  name: string;
  display_name: string;
}

type NotificationType = 'push' | 'sms' | 'both';

export default function SubscribeScreen() {
  const [resorts, setResorts] = useState<Resort[]>([]);
  const [selectedResort, setSelectedResort] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [notificationType, setNotificationType] = useState<NotificationType>('push');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingResorts, setLoadingResorts] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchResorts = async () => {
      try {
        const resortList = await getResorts();
        setResorts(resortList);
      } catch (error) {
        console.error('Error fetching resorts:', error);
        Alert.alert('Error', 'Failed to load resorts');
      } finally {
        setLoadingResorts(false);
      }
    };

    fetchResorts();

    // Set default date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setSelectedDate(tomorrow.toISOString().split('T')[0]);
  }, []);

  const handleSubscribe = async () => {
    if (!selectedResort) {
      Alert.alert('Error', 'Please select a resort');
      return;
    }

    if (!selectedDate) {
      Alert.alert('Error', 'Please select a date');
      return;
    }

    if ((notificationType === 'sms' || notificationType === 'both') && !phoneNumber) {
      Alert.alert('Error', 'Please enter a phone number for SMS notifications');
      return;
    }

    setLoading(true);

    try {
      const { deviceId, authToken } = await getCredentials();
      if (!deviceId || !authToken) {
        Alert.alert('Error', 'Not logged in');
        return;
      }

      await subscribeDevice(
        deviceId,
        selectedResort,
        selectedDate,
        authToken,
        notificationType,
        notificationType !== 'push' ? phoneNumber : undefined
      );

      Alert.alert('Success', 'You will be notified when parking becomes available!', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (error) {
      Alert.alert(
        'Error',
        error instanceof Error ? error.message : 'Failed to subscribe'
      );
    } finally {
      setLoading(false);
    }
  };

  if (loadingResorts) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Select Resort</Text>
        <View style={styles.optionsGrid}>
          {resorts.map((resort) => (
            <TouchableOpacity
              key={resort.name}
              style={[
                styles.option,
                selectedResort === resort.name && styles.optionSelected,
              ]}
              onPress={() => setSelectedResort(resort.name)}
            >
              <Text
                style={[
                  styles.optionText,
                  selectedResort === resort.name && styles.optionTextSelected,
                ]}
              >
                {resort.display_name}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Select Date</Text>
        <View style={styles.calendarContainer}>
          <Calendar
            current={selectedDate}
            minDate={new Date().toISOString().split('T')[0]}
            onDayPress={(day: DateData) => setSelectedDate(day.dateString)}
            markedDates={{
              [selectedDate]: { selected: true, selectedColor: '#2563eb' },
            }}
            theme={{
              backgroundColor: '#ffffff',
              calendarBackground: '#ffffff',
              textSectionTitleColor: '#6b7280',
              selectedDayBackgroundColor: '#2563eb',
              selectedDayTextColor: '#ffffff',
              todayTextColor: '#2563eb',
              dayTextColor: '#1f2937',
              textDisabledColor: '#d1d5db',
              arrowColor: '#2563eb',
              monthTextColor: '#1f2937',
              textMonthFontWeight: '600',
              textDayFontSize: 14,
              textMonthFontSize: 16,
              textDayHeaderFontSize: 12,
            }}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notification Type</Text>
        <View style={styles.optionsGrid}>
          {(['push', 'sms', 'both'] as NotificationType[]).map((type) => (
            <TouchableOpacity
              key={type}
              style={[
                styles.option,
                notificationType === type && styles.optionSelected,
              ]}
              onPress={() => setNotificationType(type)}
            >
              <Text
                style={[
                  styles.optionText,
                  notificationType === type && styles.optionTextSelected,
                ]}
              >
                {type === 'push' ? '📱 Push Only' : type === 'sms' ? '💬 SMS Only' : '📱💬 Both'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {(notificationType === 'sms' || notificationType === 'both') && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Phone Number</Text>
          <TextInput
            style={styles.input}
            placeholder="+1 (555) 123-4567"
            value={phoneNumber}
            onChangeText={setPhoneNumber}
            keyboardType="phone-pad"
            autoComplete="tel"
          />
        </View>
      )}

      <TouchableOpacity
        style={[styles.submitButton, loading && styles.submitButtonDisabled]}
        onPress={handleSubscribe}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitButtonText}>Subscribe</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 12,
  },
  optionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  calendarContainer: {
    backgroundColor: '#fff',
    borderRadius: 8,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: '#e5e7eb',
  },
  option: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#e5e7eb',
  },
  optionSelected: {
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  optionText: {
    fontSize: 14,
    color: '#374151',
  },
  optionTextSelected: {
    color: '#2563eb',
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  submitButton: {
    backgroundColor: '#2563eb',
    marginHorizontal: 16,
    marginVertical: 24,
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  submitButtonDisabled: {
    opacity: 0.7,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
