// =============================================================
// app.js — Habelite Recon Portal
// =============================================================

// ── Drop zone wiring ──────────────────────────────────────────
function wireDropZone(zoneId, inputId, tagId, multiple) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const tags = document.getElementById(tagId);
  if (!zone || !input) return;

  function showTags(files) {
    if (!tags) return;
    tags.innerHTML = "";
    Array.from(files).forEach((f) => {
      const span = document.createElement("span");
      span.className = "file-tag";
      span.textContent = f.name;
      tags.appendChild(span);
    });
  }

  input.addEventListener("change", () => showTags(input.files));

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
    const dt = new DataTransfer();
    filtered.forEach((f) => dt.items.add(f));
    input.files = dt.files;
    showTags(input.files);
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
