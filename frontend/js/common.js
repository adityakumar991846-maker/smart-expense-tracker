/**
 * Common utilities, UI initializers, and navigation bindings.
 */
const Common = {
  initLayout() {
    this.highlightActiveNav();
    this.populateUserHeader();
    this.bindLogoutButtons();
  },

  highlightActiveNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link, .sidebar-nav-link');

    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && (currentPath.endsWith(href) || currentPath.includes(href.replace('.html', '')))) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  },

  populateUserHeader() {
    const user = Auth.getUser();
    if (user) {
      const nameElements = document.querySelectorAll('.user-display-name');
      const emailElements = document.querySelectorAll('.user-display-email');

      nameElements.forEach(el => {
        el.textContent = user.display_name || user.full_name || 'User';
      });

      emailElements.forEach(el => {
        el.textContent = user.email || '';
      });
    }
  },

  bindLogoutButtons() {
    const logoutBtns = document.querySelectorAll('.btn-logout, #logoutBtn');
    logoutBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        Auth.logout();
      });
    });
  },

  formatCurrency(amount, currency = '₹') {
    const num = Number(amount) || 0;
    return `${currency}${num.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  },

  formatDate(dateString) {
    if (!dateString) return '—';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return dateString;
    }
  },

  showAlert(containerId, message, type = 'danger') {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show d-flex align-items-center" role="alert">
        <i class="bi ${type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-check-circle-fill'} me-2 fs-5"></i>
        <div class="flex-grow-1">${message}</div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  },

  clearAlert(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = '';
    }
  },
};

// Initialize when DOM content is loaded
document.addEventListener('DOMContentLoaded', () => {
  Common.initLayout();
});
