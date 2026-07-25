(function () {
  'use strict';

  var widget = document.getElementById('ph-upload-widget');
  if (!widget) return;

  var API_URL = widget.dataset.api;
  var REQUIRE = widget.dataset.required !== 'false';

  if (!API_URL) {
    console.warn('[Pulse & Heirloom] Set the API upload URL in Theme Customizer → Audio Upload.');
    return;
  }

  var uploadedUrl = null;

  var dropZone   = document.getElementById('ph-drop-zone');
  var fileInput  = document.getElementById('ph-file-input');
  var progress   = document.getElementById('ph-progress');
  var fill       = document.getElementById('ph-progress-fill');
  var successEl  = document.getElementById('ph-success');
  var filenameEl = document.getElementById('ph-filename');
  var errorEl    = document.getElementById('ph-error');

  // ── Drag-and-drop ────────────────────────────────────────────────────────
  dropZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', function () {
    dropZone.classList.remove('drag-over');
  });
  dropZone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    var f = e.dataTransfer.files[0];
    if (f) uploadFile(f);
  });
  dropZone.addEventListener('click', function () { fileInput.click(); });
  dropZone.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') fileInput.click();
  });
  fileInput.addEventListener('change', function () {
    if (this.files[0]) uploadFile(this.files[0]);
  });

  // ── Upload ───────────────────────────────────────────────────────────────
  function uploadFile(file) {
    uploadedUrl = null;
    successEl.hidden = true;
    errorEl.hidden   = true;
    progress.hidden  = false;
    fill.style.width = '0%';

    var formData = new FormData();
    formData.append('file', file);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', API_URL);

    xhr.upload.addEventListener('progress', function (e) {
      if (e.lengthComputable) {
        fill.style.width = Math.round((e.loaded / e.total) * 100) + '%';
      }
    });

    xhr.addEventListener('load', function () {
      progress.hidden = true;
      if (xhr.status === 200) {
        var data = JSON.parse(xhr.responseText);
        uploadedUrl = data.url;
        filenameEl.textContent = file.name;
        successEl.hidden = false;
      } else {
        var msg = 'Upload failed — please try again.';
        try { msg = JSON.parse(xhr.responseText).detail || msg; } catch (e) {}
        showError(msg);
      }
    });

    xhr.addEventListener('error', function () {
      progress.hidden = true;
      showError('Network error — check your connection and try again.');
    });

    xhr.send(formData);
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }

  // ── Inject URL into cart form before submission ──────────────────────────
  // Runs in capture phase so it fires before any theme-level submit handlers.
  var form = document.querySelector('form[action^="/cart/add"]');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    if (REQUIRE && !uploadedUrl) {
      e.preventDefault();
      e.stopImmediatePropagation();
      showError('Please upload your recording before adding to cart.');
      widget.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    if (uploadedUrl) {
      var hidden = form.querySelector('input[name="properties[audio_file]"]');
      if (!hidden) {
        hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'properties[audio_file]';
        form.appendChild(hidden);
      }
      hidden.value = uploadedUrl;
    }
  }, true);
})();
