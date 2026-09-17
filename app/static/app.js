document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const dropContent = document.getElementById('drop-content');
  const previewContainer = document.getElementById('preview-container');
  const imagePreview = document.getElementById('image-preview');
  const pdfPreviewInfo = document.getElementById('pdf-preview-info');
  const pdfName = document.getElementById('pdf-name');
  const btnRemoveFile = document.getElementById('btn-remove-file');
  const fileLoadedInfo = document.getElementById('file-loaded-info');
  const fileLoadedName = document.getElementById('file-loaded-name');
  const fileLoadedSize = document.getElementById('file-loaded-size');

  // Privacy Redaction Elements
  const redactPiiToggle = document.getElementById('redact-pii-toggle');
  const privacyOptions = document.getElementById('privacy-options');
  const redactionStyleSelect = document.getElementById('redaction-style-select');

  const btnScan = document.getElementById('btn-scan');
  const modelSelect = document.getElementById('model-select');
  const promptInput = document.getElementById('prompt-input');
  const presetBtns = document.querySelectorAll('.preset-btn');
  const systemStatus = document.getElementById('system-status');
  const statusText = document.getElementById('status-text');

  // Output Tabs & Content
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabBtnRedacted = document.getElementById('tab-btn-redacted');
  const emptyState = document.getElementById('empty-state');
  const loadingState = document.getElementById('loading-state');
  const jsonResult = document.getElementById('json-result');
  const redactedResult = document.getElementById('redacted-result');
  const redactedImagePreview = document.getElementById('redacted-image-preview');
  const redactedMeta = document.getElementById('redacted-meta');

  const activeTimer = document.getElementById('active-timer');
  const timeTag = document.getElementById('time-tag');
  const btnCopy = document.getElementById('btn-copy');
  const btnDownload = document.getElementById('btn-download');
  const btnDownloadRedacted = document.getElementById('btn-download-redacted');

  let selectedFile = null;
  let timerInterval = null;
  let currentJsonData = null;
  let currentRedactedBase64 = null;
  let modelsLoaded = false;
  let activeTab = 'json';

  // Toggle PII privacy options visibility
  redactPiiToggle.addEventListener('change', () => {
    privacyOptions.style.display = redactPiiToggle.checked ? 'block' : 'none';
  });

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      switchTab(targetTab);
    });
  });

  function switchTab(tab) {
    activeTab = tab;
    tabBtns.forEach(b => {
      if (b.dataset.tab === tab) {
        b.classList.add('active');
      } else {
        b.classList.remove('active');
      }
    });

    if (tab === 'json') {
      if (currentJsonData) jsonResult.style.display = 'block';
      redactedResult.style.display = 'none';
    } else if (tab === 'redacted') {
      jsonResult.style.display = 'none';
      if (currentRedactedBase64) redactedResult.style.display = 'flex';
    }
  }

  // Preset Prompts
  const PROMPT_PRESETS = {
    invoice: `You are an expert accounting auditor. Extract all billing details from this INVOICE with maximum accuracy in JSON:
- Invoice number, issue date, and due date.
- Issuer / Seller details (name/company, tax ID, address, contact).
- Customer / Buyer details (name/company, tax ID, address).
- Taxable subtotal, total taxes, grand total, and currency.
- Detailed tax breakdown tier list (% tax, base, amount).
- Line item list (description, quantity, unit price, line total).
- Payment method and bank account IBAN if present.`,

    receipt: `You are an expert accountant. Extract all details from this STORE RECEIPT / TICKET in JSON:
- Merchant/store name and tax registration number.
- Date and time of purchase.
- Complete itemized list of goods or services with respective prices.
- Grand total amount paid, currency, and payment method (card/cash).
- Included sales taxes / VAT breakdown.`,

    custom: `Extract all relevant structured data from this document into clean JSON format.`
  };

  promptInput.value = PROMPT_PRESETS.invoice;

  presetBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      presetBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const key = btn.dataset.preset;
      promptInput.value = PROMPT_PRESETS[key] || '';
    });
  });

  // Backend Health & Models Check
  async function checkHealth() {
    try {
      const res = await fetch('/api/v1/health');
      const data = await res.json();
      if (data.status === 'healthy') {
        systemStatus.className = 'status-badge online';
        statusText.textContent = `Online (${data.available_models.length} model(s) ready)`;

        if (!modelsLoaded && data.available_models && data.available_models.length > 0) {
          modelSelect.innerHTML = '';
          data.available_models.forEach(model => {
            const opt = document.createElement('option');
            opt.value = model;
            const isQwen7b = model.includes('7b');
            opt.textContent = model + (isQwen7b ? ' (Recommended - Highest Precision)' : ' (Fast)');
            if (model === data.default_model) opt.selected = true;
            modelSelect.appendChild(opt);
          });
          modelsLoaded = true;
        }
      } else {
        systemStatus.className = 'status-badge offline';
        statusText.textContent = 'Ollama initializing or not started';
      }
    } catch (err) {
      systemStatus.className = 'status-badge offline';
      statusText.textContent = 'Backend server offline';
    }
  }
  checkHealth();
  setInterval(checkHealth, 10000);

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function handleFile(file) {
    if (!file) return;

    selectedFile = file;
    dropContent.style.display = 'none';
    previewContainer.style.display = 'flex';
    fileLoadedInfo.style.display = 'flex';
    fileLoadedName.textContent = file.name || 'pasted_document.png';
    fileLoadedSize.textContent = `(${formatBytes(file.size || 0)})`;

    btnScan.disabled = false;

    const isPdf = file.type === 'application/pdf' || (file.name && file.name.toLowerCase().endsWith('.pdf'));

    if (isPdf) {
      imagePreview.style.display = 'none';
      pdfPreviewInfo.style.display = 'flex';
      pdfName.textContent = file.name;
    } else {
      pdfPreviewInfo.style.display = 'none';
      imagePreview.style.display = 'block';
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreview.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  function resetFileSelection() {
    selectedFile = null;
    fileInput.value = '';
    imagePreview.src = '';
    previewContainer.style.display = 'none';
    fileLoadedInfo.style.display = 'none';
    dropContent.style.display = 'flex';
    btnScan.disabled = true;
    tabBtnRedacted.style.display = 'none';
    btnDownloadRedacted.style.display = 'none';
    currentRedactedBase64 = null;
  }

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });

  btnRemoveFile.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    resetFileSelection();
  });

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    window.addEventListener(eventName, (e) => {
      e.preventDefault();
    }, false);
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  window.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (let item of items) {
      if (item.kind === 'file') {
        const blob = item.getAsFile();
        if (blob) {
          handleFile(blob);
          break;
        }
      }
    }
  });

  // Trigger OCR & Redaction scan
  btnScan.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    btnScan.disabled = true;
    emptyState.style.display = 'none';
    jsonResult.style.display = 'none';
    redactedResult.style.display = 'none';
    loadingState.style.display = 'flex';
    timeTag.style.display = 'none';
    btnCopy.disabled = true;
    btnDownload.disabled = true;
    btnDownloadRedacted.style.display = 'none';
    tabBtnRedacted.style.display = 'none';

    const startTime = Date.now();
    activeTimer.textContent = '0.0s';
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      activeTimer.textContent = `${elapsed}s`;
    }, 100);

    const formData = new FormData();
    formData.append('file', selectedFile, selectedFile.name || 'document.png');
    formData.append('prompt', promptInput.value);
    formData.append('model', modelSelect.value);
    formData.append('force_json', 'true');
    formData.append('redact_pii', redactPiiToggle.checked ? 'true' : 'false');
    formData.append('redaction_style', redactionStyleSelect.value);

    try {
      const res = await fetch('/api/v1/extract', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      clearInterval(timerInterval);
      loadingState.style.display = 'none';

      currentJsonData = data.data || data;
      timeTag.textContent = `⏱ ${data.elapsed_seconds || 0}s`;
      timeTag.style.display = 'inline-block';
      btnCopy.disabled = false;
      btnDownload.disabled = false;

      jsonResult.querySelector('code').textContent = JSON.stringify(currentJsonData, null, 2);

      // Handle Redacted Image
      if (data.redacted_image_base64) {
        currentRedactedBase64 = data.redacted_image_base64;
        redactedImagePreview.src = 'data:image/jpeg;base64,' + data.redacted_image_base64;
        
        const count = (data.pii_boxes || []).length;
        redactedMeta.textContent = `${count} sensitive element(s) censored (${redactionStyleSelect.value})`;

        tabBtnRedacted.style.display = 'inline-block';
        btnDownloadRedacted.style.display = 'inline-block';

        // Auto-switch to redacted tab if user had checked the box
        if (redactPiiToggle.checked) {
          switchTab('redacted');
        } else {
          switchTab('json');
        }
      } else {
        switchTab('json');
      }

    } catch (err) {
      clearInterval(timerInterval);
      loadingState.style.display = 'none';
      jsonResult.style.display = 'block';
      jsonResult.querySelector('code').textContent = `Error processing document:\n${err.message}`;
    } finally {
      btnScan.disabled = false;
    }
  });

  // Copy JSON
  btnCopy.addEventListener('click', async () => {
    if (!currentJsonData) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(currentJsonData, null, 2));
      const originalText = btnCopy.textContent;
      btnCopy.textContent = '✅ Copied!';
      setTimeout(() => btnCopy.textContent = originalText, 2000);
    } catch (err) {
      alert('Manual copy required: select text and press Ctrl+C');
    }
  });

  // Download JSON
  btnDownload.addEventListener('click', () => {
    if (!currentJsonData) return;
    const blob = new Blob([JSON.stringify(currentJsonData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `invoice_data_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // Download Redacted Document Image
  btnDownloadRedacted.addEventListener('click', () => {
    if (!currentRedactedBase64) return;
    const byteCharacters = atob(currentRedactedBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `redacted_document_${Date.now()}.jpg`;
    a.click();
    URL.revokeObjectURL(url);
  });
});
