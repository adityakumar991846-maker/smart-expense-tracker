/**
 * Reusable HTTP API helper with Token Authentication and comprehensive error handling.
 */
const API = {
  getAccessToken() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  },

  setAuth(token, user) {
    if (token) {
      localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, token);
    }
    if (user) {
      localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    }
  },

  clearAuth() {
    localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_DATA);
  },

  getCurrentUser() {
    const data = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA);
    try {
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers || {}),
    };

    // If uploading FormData, delete Content-Type to allow browser boundary calculation
    if (options.body instanceof FormData) {
      delete headers['Content-Type'];
    }

    // Attach Token authorization if requested or if token exists
    if (options.auth !== false) {
      const token = this.getAccessToken();
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }
    }

    try {
      const response = await fetch(url, {
        method: options.method || 'GET',
        headers,
        body: options.body instanceof FormData ? options.body : (options.body ? JSON.stringify(options.body) : undefined),
      });

      // Handle 401 Unauthorized
      if (response.status === 401) {
        this.clearAuth();
        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html')) {
          window.location.href = '/frontend/login.html?expired=1';
        }
        return {
          status: 401,
          ok: false,
          error: 'Your session has expired. Please log in again.',
        };
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return { status: 204, ok: true, data: null };
      }

      let data;
      try {
        data = await response.json();
      } catch (err) {
        data = null;
      }

      if (!response.ok) {
        // Extract human readable error
        let errorMessage = 'An unexpected error occurred. Please try again.';
        if (data) {
          if (typeof data.error === 'string') {
            errorMessage = data.error;
          } else if (typeof data.message === 'string') {
            errorMessage = data.message;
          } else if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (data.errors && typeof data.errors === 'object') {
            const firstKey = Object.keys(data.errors)[0];
            const val = data.errors[firstKey];
            errorMessage = Array.isArray(val) ? `${firstKey}: ${val[0]}` : String(val);
          } else if (typeof data === 'object') {
            const firstKey = Object.keys(data)[0];
            const val = data[firstKey];
            errorMessage = Array.isArray(val) ? `${firstKey}: ${val[0]}` : String(val);
          }
        } else if (response.status === 403) {
          errorMessage = 'You do not have permission to perform this action.';
        } else if (response.status === 404) {
          errorMessage = 'The requested resource was not found.';
        } else if (response.status >= 500) {
          errorMessage = 'Server error. Please try again in a few moments.';
        }

        return {
          status: response.status,
          ok: false,
          error: errorMessage,
          rawErrors: data && data.errors ? data.errors : data,
        };
      }

      return {
        status: response.status,
        ok: true,
        data,
      };
    } catch (networkError) {
      console.error('Network request failed:', networkError);
      return {
        status: 0,
        ok: false,
        error: 'Unable to connect to the server. Please verify your connection.',
      };
    }
  },

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  },

  post(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  },

  put(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', body });
  },

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  },
};
