/**
 * Registration Page Controller
 */
document.addEventListener('DOMContentLoaded', () => {
  if (Auth.redirectIfAuth()) return;

  const registerForm = document.getElementById('registerForm');
  const fullNameInput = document.getElementById('fullName');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const submitBtn = document.getElementById('submitBtn');
  const alertContainerId = 'registerAlert';

  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      Common.clearAlert(alertContainerId);

      const fullName = fullNameInput.value.trim();
      const email = emailInput.value.trim();
      const password = passwordInput.value;
      const confirmPassword = confirmPasswordInput.value;

      // Client-side validations
      if (!fullName) {
        Common.showAlert(alertContainerId, 'Please enter your full name.');
        fullNameInput.focus();
        return;
      }

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

      if (password.length < 6) {
        Common.showAlert(alertContainerId, 'Password must be at least 6 characters long.');
        passwordInput.focus();
        return;
      }

      if (password !== confirmPassword) {
        Common.showAlert(alertContainerId, 'Passwords do not match. Please verify.');
        confirmPasswordInput.focus();
        return;
      }

      // Set loading state
      const originalBtnText = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Creating account...';

      try {
        const response = await API.post(CONFIG.ENDPOINTS.REGISTER, {
          full_name: fullName,
          email,
          password,
          confirm_password: confirmPassword,
        }, { auth: false });

        if (!response.ok) {
          let errorMsg = response.error || 'Failed to create account.';
          if (response.rawErrors) {
            if (response.rawErrors.email) {
              errorMsg = Array.isArray(response.rawErrors.email) ? response.rawErrors.email[0] : response.rawErrors.email;
            } else if (response.rawErrors.confirm_password) {
              errorMsg = Array.isArray(response.rawErrors.confirm_password) ? response.rawErrors.confirm_password[0] : response.rawErrors.confirm_password;
            }
          }
          Common.showAlert(alertContainerId, errorMsg, 'danger');
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnText;
          return;
        }

        // Redirect to login page upon success
        window.location.href = '/frontend/login.html?registered=1';
      } catch (err) {
        Common.showAlert(alertContainerId, 'An unexpected connection error occurred.', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
      }
    });
  }
});
