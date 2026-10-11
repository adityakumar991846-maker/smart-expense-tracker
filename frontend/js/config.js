/**
 * Application Configuration & API Endpoints
 */
const CONFIG = {
  API_BASE_URL: window.SMART_EXPENSE_API_BASE_URL || '/api',
  ENDPOINTS: {
    // Auth
    REGISTER: '/auth/register/',
    LOGIN: '/auth/login/',
    LOGOUT: '/auth/logout/',
    PROFILE: '/auth/profile/',
    CHANGE_PASSWORD: '/auth/change-password/',

    // Categories
    CATEGORIES: '/categories/',

    // Expenses
    EXPENSES: '/expenses/',
    CHECK_DUPLICATE: '/expenses/check-duplicate/',

    // Dashboard
    DASHBOARD_SUMMARY: '/dashboard/summary/',
    CATEGORY_SUMMARY: '/dashboard/category-summary/',
    MONTHLY_SUMMARY: '/dashboard/monthly-summary/',

    // Reports
    REPORTS: '/reports/',

    // OCR (Phase 3)
    OCR_ANALYZE: '/ocr/analyze/',
    OCR_CONFIRM: '/ocr/confirm/',
  },
  STORAGE_KEYS: {
    AUTH_TOKEN: 'smart_expense_token',
    USER_DATA: 'smart_expense_user',
  },
  DEFAULT_CURRENCY: '₹',
};

// Freeze configuration
Object.freeze(CONFIG);
Object.freeze(CONFIG.ENDPOINTS);
Object.freeze(CONFIG.STORAGE_KEYS);
