/**
 * OCR Screenshot Scanning & Confirmation Controller (Phase 3)
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!Auth.requireAuth()) return;

  const dropzone = document.getElementById('dropzoneArea');
  const fileInput = document.getElementById('screenshotInput');
  const chooseBtn = document.getElementById('chooseFileBtn');
  const previewArea = document.getElementById('previewArea');
  const previewImg = document.getElementById('imagePreview');
  const fileNameText = document.getElementById('fileNameText');
  const fileSizeText = document.getElementById('fileSizeText');
  const removeBtn = document.getElementById('removeImageBtn');
  const analyzeBtn = document.getElementById('analyzeBtn');

  const loadingArea = document.getElementById('ocrLoadingArea');
  const resultArea = document.getElementById('ocrResultArea');
  const successArea = document.getElementById('ocrSuccessArea');

  const ocrForm = document.getElementById('ocrForm');
  const ocrAlertContainer = 'ocrAlert';
  const duplicateAlertBox = document.getElementById('duplicateAlertBox');
  const duplicateMsg = document.getElementById('duplicateMsg');

  const scanAnotherBtn = document.getElementById('scanAnotherBtn');
  const confirmBtn = document.getElementById('confirmExpenseBtn');

  let currentFile = null;
  let categoriesList = [];

  // Load categories for dropdown
  try {
    const catRes = await API.get(CONFIG.ENDPOINTS.CATEGORIES);
    if (catRes.ok && catRes.data.results) {
      categoriesList = catRes.data.results;
      populateCategorySelect('ocrCategory', categoriesList);
    }
  } catch (e) {
    console.warn('Failed to load categories:', e);
  }

  function populateCategorySelect(selectId, categories, selectedId = null, selectedName = null) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = '<option value="">Select Category</option>';
    categories.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      if (selectedId && c.id === selectedId) {
        opt.selected = true;
      } else if (selectedName && c.name.toLowerCase() === selectedName.toLowerCase()) {
        opt.selected = true;
      }
      sel.appendChild(opt);
    });
  }

  // File selection bindings
  chooseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener('click', () => {
    fileInput.click();
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  });

  removeBtn.addEventListener('click', resetToUploadState);

  if (scanAnotherBtn) {
    scanAnotherBtn.addEventListener('click', resetToUploadState);
  }

  function resetToUploadState() {
    currentFile = null;
    fileInput.value = '';
    previewImg.src = '';
    dropzone.classList.remove('d-none');
    previewArea.classList.add('d-none');
    if (loadingArea) loadingArea.classList.add('d-none');
    if (resultArea) resultArea.classList.add('d-none');
    if (successArea) successArea.classList.add('d-none');
    Common.clearAlert(ocrAlertContainer);
  }

  function handleFile(file) {
    Common.clearAlert(ocrAlertContainer);
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      Common.showAlert(ocrAlertContainer, 'Please upload a valid JPG, PNG, or WEBP image.');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      Common.showAlert(ocrAlertContainer, 'Image size exceeds the 5 MB limit.');
      return;
    }

    currentFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
      previewImg.src = event.target.result;
      fileNameText.textContent = file.name;
      fileSizeText.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';

      dropzone.classList.add('d-none');
      previewArea.classList.remove('d-none');
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = '<i class="bi bi-cpu me-2"></i>Analyze Payment Screenshot';
    };
    reader.readAsDataURL(file);
  }

  // Analyze button click
  analyzeBtn.addEventListener('click', async () => {
    if (!currentFile) return;

    previewArea.classList.add('d-none');
    loadingArea.classList.remove('d-none');
    Common.clearAlert(ocrAlertContainer);

    const formData = new FormData();
    formData.append('image', currentFile);

    try {
      const response = await API.post(CONFIG.ENDPOINTS.OCR_ANALYZE, formData);

      loadingArea.classList.add('d-none');

      if (!response.ok) {
        previewArea.classList.remove('d-none');
        Common.showAlert(ocrAlertContainer, response.error || 'Failed to process image with OCR.');
        return;
      }

      const { extracted_data, duplicate_warning } = response.data;
      displayOcrResult(extracted_data, duplicate_warning);

    } catch (err) {
      loadingArea.classList.add('d-none');
      previewArea.classList.remove('d-none');
      Common.showAlert(ocrAlertContainer, 'Network failure while processing OCR. Please try again.');
    }
  });

  function displayOcrResult(data, duplicateWarning) {
    resultArea.classList.remove('d-none');

    document.getElementById('ocrAmount').value = data.amount !== null ? data.amount : '';
    document.getElementById('ocrMerchant').value = data.merchant_name || '';
    document.getElementById('ocrDate').value = data.transaction_date || new Date().toISOString().split('T')[0];
    document.getElementById('ocrTime').value = data.transaction_time || '';
    document.getElementById('ocrMethod').value = data.payment_method || 'Google Pay / UPI';
    document.getElementById('ocrStatus').value = data.payment_status || 'Completed';
    document.getElementById('ocrUpiId').value = data.upi_transaction_id || '';
    document.getElementById('ocrGoogleId').value = data.google_transaction_id || '';
    document.getElementById('ocrBank').value = data.bank_name || '';
    document.getElementById('ocrVpa').value = data.upi_id || '';

    populateCategorySelect('ocrCategory', categoriesList, data.category_id, data.suggested_category);

    // Duplicate detection warning banner
    if (duplicateWarning && duplicateWarning.is_duplicate) {
      duplicateAlertBox.classList.remove('d-none');
      duplicateMsg.innerHTML = `
        <strong>Warning:</strong> A matching transaction (₹${duplicateWarning.existing_amount} to "${escapeHtml(duplicateWarning.existing_merchant)}" on ${duplicateWarning.existing_date}) already exists in your account.
      `;
      confirmBtn.textContent = 'Save Anyway';
      confirmBtn.setAttribute('data-force-save', 'true');
    } else {
      duplicateAlertBox.classList.add('d-none');
      confirmBtn.textContent = 'Confirm & Add Expense';
      confirmBtn.removeAttribute('data-force-save');
    }
  }

  // Confirm and Add Expense
  if (ocrForm) {
    ocrForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      Common.clearAlert('ocrConfirmAlert');

      const amountVal = document.getElementById('ocrAmount').value;
      const merchantVal = document.getElementById('ocrMerchant').value.trim();
      const dateVal = document.getElementById('ocrDate').value;

      if (!amountVal || Number(amountVal) <= 0) {
        Common.showAlert('ocrConfirmAlert', "Amount could not be detected or is invalid. Please enter a valid amount.");
        return;
      }

      if (!merchantVal) {
        Common.showAlert('ocrConfirmAlert', "Merchant or receiver name is required.");
        return;
      }

      if (!dateVal) {
        Common.showAlert('ocrConfirmAlert', "Transaction date is required.");
        return;
      }

      const forceSave = confirmBtn.getAttribute('data-force-save') === 'true';

      const payload = {
        amount: parseFloat(amountVal),
        merchant_name: merchantVal,
        expense_date: dateVal,
        expense_time: document.getElementById('ocrTime').value || null,
        category_id: document.getElementById('ocrCategory').value ? parseInt(document.getElementById('ocrCategory').value) : null,
        payment_method: document.getElementById('ocrMethod').value,
        payment_status: document.getElementById('ocrStatus').value,
        upi_transaction_id: document.getElementById('ocrUpiId').value.trim() || null,
        google_transaction_id: document.getElementById('ocrGoogleId').value.trim() || null,
        bank_name: document.getElementById('ocrBank').value.trim() || null,
        upi_id: document.getElementById('ocrVpa').value.trim() || null,
        description: document.getElementById('ocrDescription').value.trim(),
        force_save: forceSave
      };

      const originalBtnText = confirmBtn.innerHTML;
      confirmBtn.disabled = true;
      confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving expense...';

      try {
        const response = await API.post(CONFIG.ENDPOINTS.OCR_CONFIRM, payload);

        if (!response.ok) {
          if (response.status === 409 || response.data?.is_duplicate) {
            duplicateAlertBox.classList.remove('d-none');
            duplicateMsg.innerHTML = '<strong>Duplicate detected:</strong> This transaction may already exist.';
            confirmBtn.textContent = 'Save Anyway';
            confirmBtn.setAttribute('data-force-save', 'true');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Save Anyway';
            return;
          }

          Common.showAlert('ocrConfirmAlert', response.error || 'Failed to save expense.');
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = originalBtnText;
          return;
        }

        // Show Success screen
        resultArea.classList.add('d-none');
        successArea.classList.remove('d-none');

        const successDetails = document.getElementById('successDetails');
        if (successDetails && response.data.expense) {
          const exp = response.data.expense;
          successDetails.innerHTML = `
            <strong>${escapeHtml(exp.merchant_name)}</strong> — ₹${Number(exp.amount).toFixed(2)} on ${Common.formatDate(exp.expense_date)}
          `;
        }

      } catch (err) {
        Common.showAlert('ocrConfirmAlert', 'Connection error while saving expense.');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalBtnText;
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
