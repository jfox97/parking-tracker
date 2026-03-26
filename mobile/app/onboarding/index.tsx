import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { registerDeviceWithCode } from '../../services/auth';
import { verifyInvitationCode } from '../../services/api';

export default function OnboardingScreen() {
  const [invitationCode, setInvitationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [codeValid, setCodeValid] = useState<boolean | null>(null);
  const router = useRouter();

  const handleVerifyCode = async (code: string) => {
    if (code.length < 3) {
      setCodeValid(null);
      return;
    }

    setVerifying(true);
    try {
      const valid = await verifyInvitationCode(code);
      setCodeValid(valid);
    } catch {
      setCodeValid(false);
    } finally {
      setVerifying(false);
    }
  };

  const handleCodeChange = (text: string) => {
    const cleaned = text.toUpperCase().replace(/[^A-Z0-9]/g, '');
    setInvitationCode(cleaned);
    setCodeValid(null);

    // Verify code after a short delay
    if (cleaned.length >= 3) {
      const timeoutId = setTimeout(() => handleVerifyCode(cleaned), 500);
      return () => clearTimeout(timeoutId);
    }
  };

  const handleRegister = async () => {
    if (!invitationCode) {
      Alert.alert('Error', 'Please enter an invitation code');
      return;
    }

    setLoading(true);

    try {
      const result = await registerDeviceWithCode(invitationCode);

      if (result.success) {
        router.replace('/');
      } else {
        Alert.alert('Error', result.error || 'Registration failed');
      }
    } catch (error) {
      Alert.alert(
        'Error',
        error instanceof Error ? error.message : 'Registration failed'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Parking Tracker</Text>
          <Text style={styles.subtitle}>
            Get notified when ski resort parking becomes available
          </Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>Invitation Code</Text>
          <View style={styles.inputContainer}>
            <TextInput
              style={[
                styles.input,
                codeValid === true && styles.inputValid,
                codeValid === false && styles.inputInvalid,
              ]}
              placeholder="Enter your code"
              value={invitationCode}
              onChangeText={handleCodeChange}
              autoCapitalize="characters"
              autoCorrect={false}
              maxLength={20}
            />
            {verifying && (
              <ActivityIndicator
                style={styles.inputIndicator}
                size="small"
                color="#6b7280"
              />
            )}
            {!verifying && codeValid === true && (
              <Text style={styles.inputCheckmark}>✓</Text>
            )}
            {!verifying && codeValid === false && (
              <Text style={styles.inputX}>✗</Text>
            )}
          </View>
          {codeValid === false && (
            <Text style={styles.errorText}>Invalid or expired code</Text>
          )}

          <TouchableOpacity
            style={[
              styles.button,
              (!invitationCode || loading || codeValid === false) &&
                styles.buttonDisabled,
            ]}
            onPress={handleRegister}
            disabled={!invitationCode || loading || codeValid === false}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Get Started</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Don't have a code? Contact the app administrator.
          </Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2563eb',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
    lineHeight: 24,
  },
  form: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 5,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  inputContainer: {
    position: 'relative',
  },
  input: {
    backgroundColor: '#f9fafb',
    borderWidth: 2,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 16,
    fontSize: 18,
    fontFamily: 'monospace',
    letterSpacing: 2,
    textAlign: 'center',
  },
  inputValid: {
    borderColor: '#22c55e',
    backgroundColor: '#f0fdf4',
  },
  inputInvalid: {
    borderColor: '#ef4444',
    backgroundColor: '#fef2f2',
  },
  inputIndicator: {
    position: 'absolute',
    right: 16,
    top: 18,
  },
  inputCheckmark: {
    position: 'absolute',
    right: 16,
    top: 14,
    fontSize: 24,
    color: '#22c55e',
  },
  inputX: {
    position: 'absolute',
    right: 16,
    top: 14,
    fontSize: 24,
    color: '#ef4444',
  },
  errorText: {
    color: '#ef4444',
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#2563eb',
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    marginTop: 32,
    alignItems: 'center',
  },
  footerText: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 14,
    textAlign: 'center',
  },
});
