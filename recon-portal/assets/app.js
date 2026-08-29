// =============================================================
// app.js — Optex Recon Portal
// =============================================================

// ── Byte formatting ──────────────────────────────────────────
function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(
    units.length - 1,
    Math.floor(Math.log(bytes) / Math.log(1024)),
  );
  const value = bytes / Math.pow(1024, i);
  const shown = i === 0 || value >= 10 ? Math.round(value) : value.toFixed(1);
  return `${shown} ${units[i]}`;
}

// ── Combined upload size check (mirrors the server's post_max_size) ──
function checkTotalUploadSize() {
  const limits = window.UPLOAD_LIMITS;
  const totalErr = document.getElementById("total-size-error");
  const runBtn = document.getElementById("run-btn");
  if (!limits || !limits.totalBytes || !totalErr) return true;

  const excelInput = document.getElementById("excel-input");
  const pdfInput = document.getElementById("pdf-input");
  let total = 0;
  if (excelInput) Array.from(excelInput.files).forEach((f) => (total += f.size));
  if (pdfInput) Array.from(pdfInput.files).forEach((f) => (total += f.size));

  if (total > limits.totalBytes) {
    totalErr.textContent =
      `Combined upload is ${formatBytes(total)}, which exceeds the ` +
      `${limits.totalHuman} maximum allowed per submission. Remove or split up some files.`;
    if (runBtn) runBtn.disabled = true;
    return false;
  }

  totalErr.textContent = "";
  if (runBtn) runBtn.disabled = false;
  return true;
}

// ── Drop zone wiring ──────────────────────────────────────────
function wireDropZone(zoneId, inputId, tagId, multiple, errorId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const tags = document.getElementById(tagId);
  const errorEl = errorId ? document.getElementById(errorId) : null;
  if (!zone || !input) return;

  function showTags(files) {
    if (!tags) return;
    tags.innerHTML = "";
    Array.from(files).forEach((f) => {
      const span = document.createElement("span");
      span.className = "file-tag";
      span.textContent = `${f.name} (${formatBytes(f.size)})`;
      tags.appendChild(span);
    });
  }

  // Reject any file bigger than the server's per-file limit, reporting
  // exactly how big it was next to what the server will actually accept.
  function enforceSizeLimit(files) {
    const limits = window.UPLOAD_LIMITS;
    if (!limits || !limits.perFileBytes) return files;

    const oversized = files.filter((f) => f.size > limits.perFileBytes);
    const accepted = files.filter((f) => f.size <= limits.perFileBytes);

    if (errorEl) {
      errorEl.textContent = oversized.length
        ? oversized
            .map(
              (f) =>
                `${f.name} is ${formatBytes(f.size)} — the maximum allowed file size is ${limits.perFileHuman}.`,
            )
            .join(" ")
        : "";
    }
    return accepted;
  }

  function applyFiles(fileList) {
    const accepted = enforceSizeLimit(Array.from(fileList));
    const dt = new DataTransfer();
    accepted.forEach((f) => dt.items.add(f));
    input.files = dt.files;
    showTags(input.files);
    checkTotalUploadSize();
  }

  input.addEventListener("change", () => applyFiles(input.files));

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", (e) => {
    if (!zone.contains(e.relatedTarget)) zone.classList.remove("drag-over");
  });
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    const allowed = multiple
      ? (f) => f.name.toLowerCase().endsWith(".pdf")
      : (f) =>
          f.name.toLowerCase().endsWith(".xlsx") ||
          f.name.toLowerCase().endsWith(".xls");
    const filtered = Array.from(files).filter(allowed);
    if (!filtered.length) {
      alert(
        multiple
          ? "Please drop PDF files only."
          : "Please drop an Excel file (.xlsx) only.",
      );
      return;
    }
    applyFiles(filtered);
  });
}

// ── Modal helpers ─────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id)?.classList.add("active");
}
function closeModal(id) {
  document.getElementById(id)?.classList.remove("active");
}

// Close modal on backdrop click
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-backdrop")) {
    e.target.classList.remove("active");
  }
});

// ── Confirm delete ────────────────────────────────────────────
function confirmDelete(msg, formId) {
  if (confirm(msg || "Are you sure?")) {
    document.getElementById(formId)?.submit();
  }
}

// ── Auto-dismiss alerts ───────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert[data-auto-dismiss]").forEach((el) => {
    setTimeout(() => el.remove(), 4000);
  });
});
