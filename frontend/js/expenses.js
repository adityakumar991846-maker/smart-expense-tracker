/**
 * Expenses List & Management Controller
 * Handles search, category filtering, sorting, pagination, and deletion via real DRF APIs.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!Auth.requireAuth()) return;

  const tableBody = document.getElementById('expenseTableBody');
  const emptyState = document.getElementById('expenseEmptyState');
  const searchInput = document.getElementById('searchInput');
  const categoryFilter = document.getElementById('categoryFilter');
  const paymentFilter = document.getElementById('paymentFilter');
  const sortFilter = document.getElementById('sortFilter');
  const paginationContainer = document.getElementById('paginationControls');
  const totalCountEl = document.getElementById('totalExpenseCount');

  let currentPage = 1;
  let searchTimeout = null;

  // Load category options into dropdown
  await loadCategoryOptions();

  // Initial load
  await fetchExpenses();

  // Search input debounce
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        currentPage = 1;
        fetchExpenses();
      }, 350);
    });
  }

  // Filter change listeners
  if (categoryFilter) categoryFilter.addEventListener('change', () => { currentPage = 1; fetchExpenses(); });
  if (paymentFilter) paymentFilter.addEventListener('change', () => { currentPage = 1; fetchExpenses(); });
  if (sortFilter) sortFilter.addEventListener('change', () => { currentPage = 1; fetchExpenses(); });

  async function loadCategoryOptions() {
    if (!categoryFilter) return;
    try {
      const response = await API.get(CONFIG.ENDPOINTS.CATEGORIES);
      if (response.ok && response.data.results) {
        response.data.results.forEach(cat => {
          const opt = document.createElement('option');
          opt.value = cat.id;
          opt.textContent = cat.name;
          categoryFilter.appendChild(opt);
        });
      }
    } catch (e) {
      console.warn('Could not load categories filter list:', e);
    }
  }

  async function fetchExpenses() {
    if (!tableBody) return;

    // Build query params
    const params = new URLSearchParams();
    params.set('page', currentPage);

    const searchVal = searchInput ? searchInput.value.trim() : '';
    if (searchVal) params.set('search', searchVal);

    const catVal = categoryFilter ? categoryFilter.value : '';
    if (catVal) params.set('category', catVal);

    const payVal = paymentFilter ? paymentFilter.value : '';
    if (payVal) params.set('payment_method', payVal);

    const sortVal = sortFilter ? sortFilter.value : 'newest';
    if (sortVal) params.set('sort_by', sortVal);

    // Show loading spinner in table
    tableBody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
          <span class="text-muted">Loading expenses...</span>
        </td>
      </tr>
    `;

    try {
      const response = await API.get(`${CONFIG.ENDPOINTS.EXPENSES}?${params.toString()}`);

      if (!response.ok) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="8" class="text-center py-4 text-danger">
              <i class="bi bi-exclamation-triangle me-2"></i> ${escapeHtml(response.error || 'Failed to load expenses.')}
            </td>
          </tr>
        `;
        return;
      }

      const { count, results, next, previous } = response.data;
      if (totalCountEl) totalCountEl.textContent = `${count} total`;

      if (!results || results.length === 0) {
        tableBody.innerHTML = '';
        if (emptyState) emptyState.classList.remove('d-none');
        if (paginationContainer) paginationContainer.innerHTML = '';
        return;
      }

      if (emptyState) emptyState.classList.add('d-none');

      tableBody.innerHTML = results.map(item => `
        <tr>
          <td class="align-middle fw-medium">${Common.formatDate(item.expense_date)}</td>
          <td class="align-middle">
            <div class="fw-semibold text-dark">${escapeHtml(item.merchant_name)}</div>
            ${item.description ? `<small class="text-muted text-truncate d-block" style="max-width: 200px;">${escapeHtml(item.description)}</small>` : ''}
          </td>
          <td class="align-middle fw-bold text-dark fs-6">${Common.formatCurrency(item.amount)}</td>
          <td class="align-middle">
            <span class="badge bg-light text-dark border">
              <i class="bi bi-tag me-1 text-primary"></i>${escapeHtml(item.category_name || 'Other')}
            </span>
          </td>
          <td class="align-middle small text-secondary">${escapeHtml(item.payment_method)}</td>
          <td class="align-middle">
            <span class="badge ${item.source === 'Screenshot OCR' ? 'bg-info text-dark' : 'bg-secondary text-white'}">
              ${escapeHtml(item.source)}
            </span>
          </td>
          <td class="align-middle">
            <span class="badge bg-success-subtle text-success border border-success-subtle">
              ${escapeHtml(item.status)}
            </span>
          </td>
          <td class="align-middle text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-primary btn-view-expense" data-expense='${escapeHtml(JSON.stringify(item))}' title="View details">
                <i class="bi bi-eye"></i>
              </button>
              <button class="btn btn-outline-danger btn-delete-expense" data-id="${item.id}" data-merchant="${escapeHtml(item.merchant_name)}" title="Delete expense">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `).join('');

      // Bind view details buttons
      document.querySelectorAll('.btn-view-expense').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const raw = e.currentTarget.getAttribute('data-expense');
          try {
            const exp = JSON.parse(raw);
            showExpenseDetailsModal(exp);
          } catch (err) {
            console.error('Failed to parse expense data:', err);
          }
        });
      });

      // Bind delete buttons
      document.querySelectorAll('.btn-delete-expense').forEach(btn => {
        btn.addEventListener('click', handleDeleteExpense);
      });

      // Render pagination
      renderPagination(count, previous, next);

    } catch (e) {
      console.error('Fetch error:', e);
      tableBody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center py-4 text-danger">Connection error while fetching expenses.</td>
        </tr>
      `;
    }
  }

  function showExpenseDetailsModal(item) {
    const modalBody = document.getElementById('expenseDetailModalBody');
    if (!modalBody) return;

    const isScreenshot = item.source === 'Screenshot OCR' || item.source === 'SCREENSHOT';

    modalBody.innerHTML = `
      <div class="mb-3">
        ${isScreenshot ? `
          <div class="alert alert-info py-2 px-3 small d-flex align-items-center mb-3">
            <i class="bi bi-camera-fill me-2 fs-6"></i>
            <span>Imported from payment screenshot</span>
          </div>
        ` : ''}

        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="text-muted small">Amount</span>
          <span class="fs-4 fw-bold text-dark">${Common.formatCurrency(item.amount)}</span>
        </div>

        <div class="list-group list-group-flush border rounded-3 p-2 small">
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Merchant / Recipient</span>
            <span class="fw-semibold text-dark text-end">${escapeHtml(item.merchant_name)}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Category</span>
            <span class="fw-semibold">${escapeHtml(item.category_name || 'Other')}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Transaction Date</span>
            <span>${Common.formatDate(item.expense_date)}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Transaction Time</span>
            <span>${item.expense_time || '—'}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Payment Method</span>
            <span>${escapeHtml(item.payment_method)}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Status</span>
            <span class="badge bg-success-subtle text-success">${escapeHtml(item.status)}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Source</span>
            <span class="badge bg-light text-dark border">${escapeHtml(item.source)}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Bank Name</span>
            <span>${item.bank_name ? escapeHtml(item.bank_name) : '—'}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">UPI ID (VPA)</span>
            <span>${item.upi_id ? escapeHtml(item.upi_id) : '—'}</span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">UPI Transaction ID</span>
            <span><code>${item.upi_transaction_id ? escapeHtml(item.upi_transaction_id) : '—'}</code></span>
          </div>
          <div class="d-flex justify-content-between py-2 border-bottom">
            <span class="text-muted">Google Transaction ID</span>
            <span><code>${item.google_transaction_id ? escapeHtml(item.google_transaction_id) : '—'}</code></span>
          </div>
          ${item.description ? `
            <div class="py-2">
              <span class="text-muted d-block mb-1">Notes:</span>
              <p class="mb-0 text-dark bg-light p-2 rounded">${escapeHtml(item.description)}</p>
            </div>
          ` : ''}
        </div>
      </div>
    `;

    const modalEl = document.getElementById('expenseDetailModal');
    if (modalEl && window.bootstrap) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    }
  }

  async function handleDeleteExpense(e) {
    const btn = e.currentTarget;
    const id = btn.getAttribute('data-id');
    const merchant = btn.getAttribute('data-merchant');

    if (!confirm(`Are you sure you want to delete the expense for "${merchant}"?`)) {
      return;
    }

    try {
      const res = await API.delete(`${CONFIG.ENDPOINTS.EXPENSES}${id}/`);
      if (res.ok) {
        fetchExpenses();
      } else {
        alert(res.error || 'Failed to delete expense.');
      }
    } catch (err) {
      alert('Error occurred while deleting expense.');
    }
  }

  function renderPagination(totalCount, prevUrl, nextUrl) {
    if (!paginationContainer) return;
    const pageSize = 10;
    const totalPages = Math.ceil(totalCount / pageSize);

    if (totalPages <= 1) {
      paginationContainer.innerHTML = '';
      return;
    }

    paginationContainer.innerHTML = `
      <nav aria-label="Expenses navigation">
        <ul class="pagination pagination-sm mb-0">
          <li class="page-item ${!prevUrl ? 'disabled' : ''}">
            <button class="page-link" id="prevPageBtn" aria-label="Previous">
              <i class="bi bi-chevron-left"></i>
            </button>
          </li>
          <li class="page-item disabled">
            <span class="page-link">Page ${currentPage} of ${totalPages}</span>
          </li>
          <li class="page-item ${!nextUrl ? 'disabled' : ''}">
            <button class="page-link" id="nextPageBtn" aria-label="Next">
              <i class="bi bi-chevron-right"></i>
            </button>
          </li>
        </ul>
      </nav>
    `;

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    if (prevBtn && prevUrl) {
      prevBtn.addEventListener('click', () => {
        currentPage = Math.max(1, currentPage - 1);
        fetchExpenses();
      });
    }
    if (nextBtn && nextUrl) {
      nextBtn.addEventListener('click', () => {
        currentPage = currentPage + 1;
        fetchExpenses();
      });
    }
  }

  function escapeHtml(text) {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }
});
