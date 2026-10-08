/**
 * Authentication state helper & route guarding
 */
const Auth = {
  isAuthenticated() {
    return !!API.getAccessToken();
  },

  getUser() {
    return API.getCurrentUser();
  },

  /**
   * For protected pages: dashboard, expenses, add-expense, scan-payment, reports, profile.
   * If not logged in, redirects immediately to login.html.
   */
  requireAuth() {
    if (!this.isAuthenticated()) {
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/frontend/login.html?next=${returnUrl}`;
      return false;
    }
    return true;
  },

  /**
   * For guest pages: login, register.
   * If already logged in, redirects to dashboard.html.
   */
  redirectIfAuth() {
    if (this.isAuthenticated()) {
      window.location.href = '/frontend/dashboard.html';
      return true;
    }
    return false;
  },

  async logout() {
    try {
      await API.post(CONFIG.ENDPOINTS.LOGOUT, {});
    } catch (e) {
      // Proceed with local logout regardless of network error
    } finally {
      API.clearAuth();
      window.location.href = '/frontend/login.html?logged_out=1';
    }
  },
};
