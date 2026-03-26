import { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { getDeviceSubscriptions, unsubscribeDevice } from '../services/api';
import { getCredentials } from '../services/auth';

interface Subscription {
  resort: string;
  date: string;
  status: string;
  notification_type: string;
  unsubscribe_token: string;
}

export default function HomeScreen() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchSubscriptions = useCallback(async () => {
    try {
      const { deviceId, authToken } = await getCredentials();
      if (deviceId && authToken) {
        const subs = await getDeviceSubscriptions(deviceId, authToken);
        setSubscriptions(subs);
      }
    } catch (error) {
      console.error('Error fetching subscriptions:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  const handleUnsubscribe = useCallback(
    async (subscription: Subscription) => {
      Alert.alert(
        'Unsubscribe',
        `Stop receiving alerts for ${formatResortName(subscription.resort)} on ${subscription.date}?`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Unsubscribe',
            style: 'destructive',
            onPress: async () => {
              try {
                await unsubscribeDevice(subscription.unsubscribe_token);
                setSubscriptions((prev) =>
                  prev.filter(
                    (s) =>
                      s.resort !== subscription.resort ||
                      s.date !== subscription.date
                  )
                );
              } catch (error) {
                Alert.alert('Error', 'Failed to unsubscribe. Please try again.');
              }
            },
          },
        ]
      );
    },
    []
  );

  const formatResortName = (name: string): string => {
    return name
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'available':
        return '#22c55e';
      case 'unavailable':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const renderSubscription = ({ item }: { item: Subscription }) => (
    <View style={styles.card}>
      <View style={styles.cardContent}>
        <Text style={styles.resortName}>{formatResortName(item.resort)}</Text>
        <Text style={styles.date}>{item.date}</Text>
        <View style={styles.statusRow}>
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: getStatusColor(item.status) },
            ]}
          >
            <Text style={styles.statusText}>
              {item.status === 'unknown' ? 'Checking...' : item.status}
            </Text>
          </View>
          <Text style={styles.notificationType}>
            {item.notification_type === 'push'
              ? '📱 Push'
              : item.notification_type === 'sms'
              ? '📱 SMS'
              : '📱 Push + SMS'}
          </Text>
        </View>
      </View>
      <TouchableOpacity
        style={styles.unsubscribeButton}
        onPress={() => handleUnsubscribe(item)}
      >
        <Text style={styles.unsubscribeText}>×</Text>
      </TouchableOpacity>
    </View>
  );

  const renderEmptyList = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyText}>No active alerts</Text>
      <Text style={styles.emptySubtext}>
        Tap the + button to subscribe to parking alerts
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={subscriptions}
        keyExtractor={(item) => `${item.resort}-${item.date}`}
        renderItem={renderSubscription}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={!loading ? renderEmptyList : null}
        contentContainerStyle={subscriptions.length === 0 ? styles.emptyList : undefined}
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push('/subscribe')}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.settingsButton}
        onPress={() => router.push('/settings')}
      >
        <Text style={styles.settingsText}>⚙️</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardContent: {
    flex: 1,
  },
  resortName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 4,
  },
  date: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 8,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
    textTransform: 'capitalize',
  },
  notificationType: {
    fontSize: 12,
    color: '#6b7280',
  },
  unsubscribeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#fee2e2',
    justifyContent: 'center',
    alignItems: 'center',
  },
  unsubscribeText: {
    color: '#ef4444',
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: -2,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#9ca3af',
    textAlign: 'center',
  },
  emptyList: {
    flex: 1,
  },
  fab: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2563eb',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
  fabText: {
    color: '#fff',
    fontSize: 32,
    fontWeight: '300',
    marginTop: -2,
  },
  settingsButton: {
    position: 'absolute',
    left: 16,
    bottom: 16,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#e5e7eb',
    justifyContent: 'center',
    alignItems: 'center',
  },
  settingsText: {
    fontSize: 24,
  },
});
