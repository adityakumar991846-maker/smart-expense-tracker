/**
 * Login Page Controller
 */
document.addEventListener('DOMContentLoaded', () => {
  // If already authenticated, redirect to dashboard
  if (Auth.redirectIfAuth()) return;

  const loginForm = document.getElementById('loginForm');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const submitBtn = document.getElementById('submitBtn');
  const alertContainerId = 'loginAlert';

  // Check URL parameters for status messages
  const params = new URLSearchParams(window.location.search);
  if (params.get('registered') === '1') {
    Common.showAlert(alertContainerId, 'Account created successfully! Please sign in with your credentials.', 'success');
  } else if (params.get('expired') === '1') {
    Common.showAlert(alertContainerId, 'Your session has expired. Please sign in again.', 'warning');
  } else if (params.get('logged_out') === '1') {
    Common.showAlert(alertContainerId, 'You have been successfully logged out.', 'info');
  }

  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      Common.clearAlert(alertContainerId);

      const email = emailInput.value.trim();
      const password = passwordInput.value;

      // Validation
      if (!email) {
        Common.showAlert(alertContainerId, 'Please enter your email address.');
        emailInput.focus();
        return;
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        Common.showAlert(alertContainerId, 'Please enter a valid email address.');
        emailInput.focus();
        return;
      }

      if (!password) {
        Common.showAlert(alertContainerId, 'Please enter your password.');
        passwordInput.focus();
        return;
      }

      // Set loading state
      const originalBtnText = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Logging in...';

      try {
        const response = await API.post(CONFIG.ENDPOINTS.LOGIN, { email, password }, { auth: false });

        if (!response.ok) {
          let errorMsg = response.error || 'Email or password is incorrect.';
          if (response.rawErrors && response.rawErrors.non_field_errors) {
            errorMsg = response.rawErrors.non_field_errors[0];
          }
          Common.showAlert(alertContainerId, errorMsg, 'danger');
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnText;
          return;
        }

        // Store authentication
        API.setAuth(response.data.token, response.data.user);

        // Redirect to target or dashboard
        const nextUrl = params.get('next');
        if (nextUrl && nextUrl.startsWith('/frontend/')) {
          window.location.href = nextUrl;
        } else {
          window.location.href = '/frontend/dashboard.html';
        }
      } catch (err) {
        Common.showAlert(alertContainerId, 'An unexpected connection error occurred.', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
      }
    });
  }
});
