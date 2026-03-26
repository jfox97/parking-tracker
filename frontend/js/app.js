/**
 * Main application logic for the Parking Tracker web interface.
 */

document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
});

/**
 * Initialize the application.
 */
async function initializeApp() {
  // Load resorts into the dropdown
  await loadResorts();

  // Set up form handlers
  setupSubscribeForm();

  // Set minimum date to today
  const dateInput = document.getElementById('date');
  if (dateInput) {
    dateInput.min = new Date().toISOString().split('T')[0];
  }
}

/**
 * Load available resorts into the dropdown.
 */
async function loadResorts() {
  const resortSelect = document.getElementById('resort');
  if (!resortSelect) return;

  try {
    const response = await ParkingAPI.getResorts();

    if (response.ok && response.data.resorts) {
      // Clear existing options except the placeholder
      resortSelect.innerHTML = '<option value="">Select a resort...</option>';

      response.data.resorts.forEach(resort => {
        const option = document.createElement('option');
        option.value = resort.name;
        option.textContent = resort.display_name;
        resortSelect.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Failed to load resorts:', error);
    showAlert('Failed to load resorts. Please refresh the page.', 'error');
  }
}

/**
 * Set up the subscribe form handler.
 */
function setupSubscribeForm() {
  const form = document.getElementById('subscribe-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // Get form data
    const phone = document.getElementById('phone').value.trim();
    const resort = document.getElementById('resort').value;
    const date = document.getElementById('date').value;
    const invitationCode = document.getElementById('invitation-code').value.trim();
    const smsConsent = document.getElementById('sms-consent').checked;

    // Basic validation
    if (!phone || !resort || !date) {
      showAlert('Please fill in all required fields.', 'error');
      return;
    }

    if (!smsConsent) {
      showAlert('You must agree to receive SMS alerts to subscribe.', 'error');
      return;
    }

    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span>Subscribing...';
    hideAlert();

    try {
      const response = await ParkingAPI.subscribe({
        phone_number: phone,
        resort: resort,
        date: date,
        invitation_code: invitationCode || undefined,
      });

      if (response.ok && response.data.success) {
        showAlert(
          `Successfully subscribed! You'll receive an SMS when parking becomes available. ` +
          `Save this link to manage your subscription.`,
          'success'
        );
        form.reset();

        // Show unsubscribe URL if provided
        if (response.data.unsubscribe_url) {
          showUnsubscribeInfo(response.data.unsubscribe_url);
        }
      } else {
        const error = response.data.error || 'Subscription failed. Please try again.';
        showAlert(error, 'error');

        // If invitation code is required, show the field more prominently
        if (error.includes('invitation code') || error.includes('Invitation code')) {
          document.getElementById('invitation-code').focus();
        }
      }
    } catch (error) {
      console.error('Subscribe error:', error);
      showAlert('Network error. Please check your connection and try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });
}

/**
 * Show an alert message.
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, error, info, warning)
 */
function showAlert(message, type = 'info') {
  const alertContainer = document.getElementById('alert-container');
  if (!alertContainer) return;

  alertContainer.innerHTML = `
    <div class="alert alert-${type}">
      ${escapeHtml(message)}
    </div>
  `;
  alertContainer.classList.remove('hidden');

  // Scroll to alert
  alertContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide the alert message.
 */
function hideAlert() {
  const alertContainer = document.getElementById('alert-container');
  if (alertContainer) {
    alertContainer.classList.add('hidden');
  }
}

/**
 * Show unsubscribe info after successful subscription.
 * @param {string} url - Unsubscribe URL
 */
function showUnsubscribeInfo(url) {
  const infoContainer = document.getElementById('unsubscribe-info');
  if (!infoContainer) return;

  infoContainer.innerHTML = `
    <div class="card">
      <h2>Subscription Created</h2>
      <p style="margin-bottom: 12px;">
        Save this link to unsubscribe later (it will also be included in alert messages):
      </p>
      <div class="code-display">
        <a href="${escapeHtml(url)}" target="_blank">${escapeHtml(url)}</a>
      </div>
    </div>
  `;
  infoContainer.classList.remove('hidden');
}

/**
 * Escape HTML to prevent XSS.
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Format a date for display.
 * @param {string} dateStr - Date in YYYY-MM-DD format
 * @returns {string} Formatted date
 */
function formatDate(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
