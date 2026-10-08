/**
 * Dashboard Controller (Phase 3)
 * Loads real metrics and powers Chart.js category doughnut and monthly trend charts.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!Auth.requireAuth()) return;

  const totalSpentEl = document.getElementById('totalSpent');
  const monthSpentEl = document.getElementById('monthSpent');
  const todaySpentEl = document.getElementById('todaySpent');
  const transactionsCountEl = document.getElementById('transactionsCount');
  const highestExpenseEl = document.getElementById('highestExpense');

  const budgetProgressEl = document.getElementById('budgetProgress');
  const budgetSpentEl = document.getElementById('budgetSpent');
  const budgetRemainingEl = document.getElementById('budgetRemaining');
  const budgetBarEl = document.getElementById('budgetBar');
  const budgetWarningAlert = document.getElementById('budgetWarningAlert');

  const recentExpensesContainer = document.getElementById('recentExpensesList');
  const categorySummaryContainer = document.getElementById('categorySummaryList');

  let categoryChartInstance = null;
  let monthlyChartInstance = null;

  try {
    const response = await API.get(CONFIG.ENDPOINTS.DASHBOARD_SUMMARY);

    if (!response.ok) {
      console.error('Failed to load dashboard metrics:', response.error);
      return;
    }

    const { metrics, budget, recent_expenses, currency = '₹' } = response.data;

    // Metric Cards
    if (totalSpentEl) totalSpentEl.textContent = Common.formatCurrency(metrics.total_spent, currency);
    if (monthSpentEl) monthSpentEl.textContent = Common.formatCurrency(metrics.month_spent, currency);
    if (todaySpentEl) todaySpentEl.textContent = Common.formatCurrency(metrics.today_spent, currency);
    if (transactionsCountEl) transactionsCountEl.textContent = metrics.transactions_count;
    if (highestExpenseEl) highestExpenseEl.textContent = Common.formatCurrency(metrics.highest_expense, currency);

    // Budget section
    if (budget && budget.monthly_budget > 0) {
      if (budgetSpentEl) budgetSpentEl.textContent = Common.formatCurrency(budget.month_spent, currency);
      if (budgetRemainingEl) budgetRemainingEl.textContent = Common.formatCurrency(budget.remaining_budget, currency);
      if (budgetBarEl) {
        budgetBarEl.style.width = `${budget.used_percentage}%`;
        budgetBarEl.setAttribute('aria-valuenow', budget.used_percentage);
        budgetBarEl.textContent = `${budget.used_percentage}%`;
        if (budget.used_percentage >= 80) {
          budgetBarEl.classList.add('bg-danger');
          budgetBarEl.classList.remove('bg-primary');
        } else {
          budgetBarEl.classList.add('bg-primary');
          budgetBarEl.classList.remove('bg-danger');
        }
      }
      if (budgetWarningAlert && budget.is_warning) {
        budgetWarningAlert.classList.remove('d-none');
      }
      if (budgetProgressEl) budgetProgressEl.classList.remove('d-none');
    }

    // Recent Expenses List
    if (recentExpensesContainer) {
      if (!recent_expenses || recent_expenses.length === 0) {
        recentExpensesContainer.innerHTML = `
          <div class="text-center py-4 text-muted">
            <i class="bi bi-inbox fs-1 d-block mb-2 text-secondary opacity-50"></i>
            <p class="mb-2">No expenses yet.</p>
            <a href="/frontend/add-expense.html" class="btn btn-sm btn-outline-primary">
              <i class="bi bi-plus-circle me-1"></i> Add your first expense
            </a>
          </div>
        `;
      } else {
        recentExpensesContainer.innerHTML = `
          <div class="list-group list-group-flush">
            ${recent_expenses.map(item => `
              <div class="list-group-item d-flex justify-content-between align-items-center px-0 py-3 border-bottom">
                <div class="d-flex align-items-center">
                  <div class="category-icon-badge me-3">
                    <i class="bi bi-receipt fs-5 text-primary"></i>
                  </div>
                  <div>
                    <h6 class="mb-0 fw-semibold">${escapeHtml(item.merchant_name)}</h6>
                    <small class="text-muted">${escapeHtml(item.category_name || 'Other')} • ${Common.formatDate(item.expense_date)}</small>
                  </div>
                </div>
                <div class="text-end">
                  <span class="fw-bold text-dark fs-6">${Common.formatCurrency(item.amount, currency)}</span>
                  <div class="text-muted small">${escapeHtml(item.payment_method)}</div>
                </div>
              </div>
            `).join('')}
          </div>
        `;
      }
    }

    // Load Charts
    await initCategoryChart(currency);
    await initMonthlyChart(currency);

  } catch (err) {
    console.error('Error in dashboard initialization:', err);
  }

  async function initCategoryChart(currency) {
    const canvas = document.getElementById('categoryDistributionChart');
    const emptyEl = document.getElementById('categoryChartEmptyState');
    if (!canvas) return;

    try {
      const res = await API.get(CONFIG.ENDPOINTS.CATEGORY_SUMMARY);
      if (res.ok && res.data.results && res.data.results.length > 0) {
        const labels = res.data.results.map(r => r.category);
        const data = res.data.results.map(r => r.total);

        // Populate sidebar category list as well
        if (categorySummaryContainer) {
          categorySummaryContainer.innerHTML = `
            <div class="list-group list-group-flush">
              ${res.data.results.map(cat => `
                <div class="list-group-item d-flex justify-content-between align-items-center px-0 py-2 border-bottom">
                  <span class="fw-medium">${escapeHtml(cat.category)}</span>
                  <span class="fw-semibold text-secondary">${Common.formatCurrency(cat.total, currency)}</span>
                </div>
              `).join('')}
            </div>
          `;
        }

        const colors = [
          '#6366f1', '#f97316', '#3b82f6', '#ec4899', '#eab308',
          '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#64748b'
        ];

        if (categoryChartInstance) categoryChartInstance.destroy();
        categoryChartInstance = new Chart(canvas, {
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
              legend: {
                position: 'bottom',
                labels: { boxWidth: 12, font: { size: 11 } }
              },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` ${ctx.label}: ${Common.formatCurrency(ctx.raw, currency)}`
                }
              }
            },
            cutout: '65%'
          }
        });

      } else {
        canvas.classList.add('d-none');
        if (emptyEl) emptyEl.classList.remove('d-none');
        if (categorySummaryContainer) {
          categorySummaryContainer.innerHTML = '<p class="text-muted small text-center py-3">No category data yet.</p>';
        }
      }
    } catch (e) {
      console.warn('Category chart error:', e);
    }
  }

  async function initMonthlyChart(currency) {
    const canvas = document.getElementById('monthlyTrendChart');
    const emptyEl = document.getElementById('monthlyEmptyState');
    if (!canvas) return;

    try {
      const res = await API.get(CONFIG.ENDPOINTS.MONTHLY_SUMMARY);
      if (res.ok && res.data.results && res.data.results.length > 0) {
        const labels = res.data.results.map(r => r.month_label);
        const data = res.data.results.map(r => r.total);

        if (monthlyChartInstance) monthlyChartInstance.destroy();
        monthlyChartInstance = new Chart(canvas, {
          type: 'bar',
          data: {
            labels,
            datasets: [{
              label: 'Monthly Spending',
              data,
              backgroundColor: '#4f46e5',
              borderRadius: 6,
              maxBarThickness: 38
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: (val) => `${currency}${val}`
                },
                grid: {
                  color: '#f1f5f9'
                }
              },
              x: {
                grid: { display: false }
              }
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` Spent: ${Common.formatCurrency(ctx.raw, currency)}`
                }
              }
            }
          }
        });
      } else {
        canvas.classList.add('d-none');
        if (emptyEl) emptyEl.classList.remove('d-none');
      }
    } catch (e) {
      console.warn('Monthly chart error:', e);
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
