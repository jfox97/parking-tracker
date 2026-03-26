/**
 * API client for the Parking Tracker web interface.
 */

const API_BASE = '/api';

/**
 * Make an API request.
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const response = await fetch(url, { ...defaultOptions, ...options });
  const data = await response.json();

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

/**
 * Get list of available resorts.
 * @returns {Promise<Object>} API response with resorts
 */
async function getResorts() {
  return apiRequest('/resorts');
}

/**
 * Verify an invitation code.
 * @param {string} code - Invitation code
 * @returns {Promise<Object>} API response
 */
async function verifyCode(code) {
  return apiRequest('/verify-code', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

/**
 * Subscribe to parking alerts.
 * @param {Object} data - Subscription data
 * @param {string} data.phone_number - Phone number
 * @param {string} data.resort - Resort name
 * @param {string} data.date - Date (YYYY-MM-DD)
 * @param {string} [data.invitation_code] - Invitation code (for new phones)
 * @returns {Promise<Object>} API response
 */
async function subscribe(data) {
  return apiRequest('/subscribe', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get subscriptions for a phone number.
 * @param {string} token - Master unsubscribe token
 * @returns {Promise<Object>} API response with subscriptions
 */
async function getSubscriptions(token) {
  return apiRequest(`/subscriptions?token=${encodeURIComponent(token)}`);
}

/**
 * Unsubscribe from a specific alert.
 * @param {string} token - Unsubscribe token
 * @returns {Promise<Object>} API response
 */
async function unsubscribe(token) {
  return apiRequest('/unsubscribe', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
}

/**
 * Unsubscribe from all alerts.
 * @param {string} token - Master unsubscribe token
 * @returns {Promise<Object>} API response
 */
async function unsubscribeAll(token) {
  return apiRequest('/unsubscribe-all', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
}

/**
 * Request an unsubscribe link to be sent via SMS.
 * @param {string} phoneNumber - Phone number to send link to
 * @returns {Promise<Object>} API response
 */
async function sendUnsubscribeLink(phoneNumber) {
  return apiRequest('/send-unsubscribe-link', {
    method: 'POST',
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
}

// Export for use in app.js
window.ParkingAPI = {
  getResorts,
  verifyCode,
  subscribe,
  getSubscriptions,
  unsubscribe,
  unsubscribeAll,
  sendUnsubscribeLink,
};
