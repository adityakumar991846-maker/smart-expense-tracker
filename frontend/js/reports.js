/**
 * Reports & Analytics Controller (Phase 3)
 * Fetches real metrics from /api/reports/, powers Chart.js charts, and handles CSV export.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!Auth.requireAuth()) return;

  const periodSelect = document.getElementById('reportPeriodSelect');
  const customDateRangeBox = document.getElementById('customDateRangeBox');
  const dateFromInput = document.getElementById('reportDateFrom');
  const dateToInput = document.getElementById('reportDateTo');
  const applyCustomBtn = document.getElementById('applyCustomRangeBtn');
  const exportCsvBtn = document.getElementById('exportCsvBtn');

  const totalSpendingEl = document.getElementById('reportTotalSpending');
  const transactionCountEl = document.getElementById('reportTransactionCount');
  const averageExpenseEl = document.getElementById('reportAverageExpense');
  const highestExpenseEl = document.getElementById('reportHighestExpense');

  const categoryTableBody = document.getElementById('reportCategoryTableBody');
  const expensesTableBody = document.getElementById('reportExpensesTableBody');
  const emptyStateEl = document.getElementById('reportEmptyState');

  let reportCategoryChart = null;

  // Set default dates
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  if (dateFromInput) dateFromInput.value = firstOfMonth.toISOString().split('T')[0];
  if (dateToInput) dateToInput.value = today.toISOString().split('T')[0];

  // Initial load
  await fetchReportData();

  // Period switch
  if (periodSelect) {
    periodSelect.addEventListener('change', () => {
      if (periodSelect.value === 'custom') {
        customDateRangeBox.classList.remove('d-none');
      } else {
        customDateRangeBox.classList.add('d-none');
        fetchReportData();
      }
    });
  }

  if (applyCustomBtn) {
    applyCustomBtn.addEventListener('click', () => {
      fetchReportData();
    });
  }

  // Export CSV
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => {
      const period = periodSelect.value;
      const params = new URLSearchParams();
      params.set('period', period);
      params.set('export', 'csv');

      if (period === 'custom') {
        if (dateFromInput.value) params.set('date_from', dateFromInput.value);
        if (dateToInput.value) params.set('date_to', dateToInput.value);
      }

      // Download CSV with authorization token
      const token = API.getAccessToken();
      const exportUrl = `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.REPORTS}?${params.toString()}`;

      fetch(exportUrl, {
        headers: { 'Authorization': `Token ${token}` }
      })
      .then(res => {
        if (!res.ok) throw new Error('Failed to generate CSV export');
        return res.blob();
      })
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `expense_report_${period}_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch(err => {
        alert('Could not export CSV report. Please try again.');
      });
    });
  }

  async function fetchReportData() {
    const period = periodSelect ? periodSelect.value : 'monthly';
    const params = new URLSearchParams();
    params.set('period', period);

    if (period === 'custom') {
      if (dateFromInput && dateFromInput.value) params.set('date_from', dateFromInput.value);
      if (dateToInput && dateToInput.value) params.set('date_to', dateToInput.value);
    }

    try {
      const response = await API.get(`${CONFIG.ENDPOINTS.REPORTS}?${params.toString()}`);

      if (!response.ok) {
        console.error('Failed to load reports:', response.error);
        return;
      }

      const { summary, category_breakdown, expenses, currency = '₹' } = response.data;

      // Update Summary metrics
      if (totalSpendingEl) totalSpendingEl.textContent = Common.formatCurrency(summary.total_spending, currency);
      if (transactionCountEl) transactionCountEl.textContent = summary.transaction_count;
      if (averageExpenseEl) averageExpenseEl.textContent = Common.formatCurrency(summary.average_expense, currency);
      if (highestExpenseEl) highestExpenseEl.textContent = Common.formatCurrency(summary.highest_expense, currency);

      // Handle Empty State
      if (!expenses || expenses.length === 0) {
        if (emptyStateEl) emptyStateEl.classList.remove('d-none');
        if (categoryTableBody) categoryTableBody.innerHTML = '<tr><td colspan="4" class="text-center py-3 text-muted">No transactions in this period.</td></tr>';
        if (expensesTableBody) expensesTableBody.innerHTML = '<tr><td colspan="6" class="text-center py-3 text-muted">No transactions in this period.</td></tr>';
        updateCategoryChart([], [], currency);
        return;
      }

      if (emptyStateEl) emptyStateEl.classList.add('d-none');

      // Populate Category Breakdown Table
      if (categoryTableBody) {
        categoryTableBody.innerHTML = category_breakdown.map(c => `
          <tr>
            <td class="fw-medium">${escapeHtml(c.category)}</td>
            <td class="fw-bold">${Common.formatCurrency(c.total, currency)}</td>
            <td class="text-secondary">${c.count}</td>
            <td>
              <div class="d-flex align-items-center">
                <span class="me-2 small fw-semibold">${c.percentage}%</span>
                <div class="progress flex-grow-1" style="height: 6px;">
                  <div class="progress-bar bg-primary" style="width: ${c.percentage}%;"></div>
                </div>
              </div>
            </td>
          </tr>
        `).join('');
      }

      // Populate Category Chart
      const catLabels = category_breakdown.map(c => c.category);
      const catData = category_breakdown.map(c => c.total);
      updateCategoryChart(catLabels, catData, currency);

      // Populate Period Expense Records Table
      if (expensesTableBody) {
        expensesTableBody.innerHTML = expenses.map(item => `
          <tr>
            <td>${Common.formatDate(item.expense_date)}</td>
            <td class="fw-semibold">${escapeHtml(item.merchant_name)}</td>
            <td class="fw-bold">${Common.formatCurrency(item.amount, currency)}</td>
            <td><span class="badge bg-light text-dark border">${escapeHtml(item.category_name || 'Other')}</span></td>
            <td class="small text-muted">${escapeHtml(item.payment_method)}</td>
            <td><span class="badge ${item.source === 'Screenshot OCR' ? 'bg-info text-dark' : 'bg-secondary text-white'}">${escapeHtml(item.source)}</span></td>
          </tr>
        `).join('');
      }

    } catch (err) {
      console.error('Error fetching report data:', err);
    }
  }

  function updateCategoryChart(labels, data, currency) {
    const canvas = document.getElementById('reportCategoryChart');
    if (!canvas) return;

    if (labels.length === 0) {
      canvas.parentElement.classList.add('d-none');
      return;
    }

    canvas.parentElement.classList.remove('d-none');

    const colors = [
      '#6366f1', '#f97316', '#3b82f6', '#ec4899', '#eab308',
      '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#64748b'
    ];

    if (reportCategoryChart) reportCategoryChart.destroy();
    reportCategoryChart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors.slice(0, labels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${Common.formatCurrency(ctx.raw, currency)}`
            }
          }
        },
        cutout: '60%'
      }
    });
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
