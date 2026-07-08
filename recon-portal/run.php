<?php
set_time_limit(300);
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_login();

$page_title = 'Run Reconciliation';
$result     = null;
$error      = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_FILES['excel_file']) || !isset($_FILES['pdf_files'])) {
        $error = 'Please upload both the Excel file and at least one PDF.';
    } else {
        $res = api_upload('/api/recon/run', $_FILES);
        if (isset($res['success']) && $res['success']) {
            $result = $res;
        } else {
            $error = $res['error'] ?? 'Reconciliation failed. Please try again.';
        }
    }
}
?>
<?php require __DIR__ . '/includes/header.php'; ?>
<?php require __DIR__ . '/includes/sidebar.php'; ?>

<div class="main-content">
  <div class="page-header">
    <h1>▶ Run Reconciliation</h1>
    <p>Upload your Client Data spreadsheet and remittance PDFs to begin.</p>
  </div>

  <?php if ($error): ?>
  <div class="alert alert-error"><?= htmlspecialchars($error) ?></div>
  <?php endif; ?>

  <?php if ($result): ?>
  <div class="alert alert-success" data-auto-dismiss>
    ✓ Reconciliation complete. Your file is downloading now.
  </div>
  <div class="card">
    <div class="card-title">Run Summary</div>
    <div class="stat-grid">
      <div class="stat-card blue">
        <div class="stat-value"><?= $result['pdf_count'] ?></div>
        <div class="stat-label">PDFs Processed</div>
      </div>
      <div class="stat-card blue">
        <div class="stat-value"><?= $result['excel_claims'] ?></div>
        <div class="stat-label">Excel Claims</div>
      </div>
      <div class="stat-card green">
        <div class="stat-value"><?= $result['matched_count'] ?></div>
        <div class="stat-label">Matched</div>
      </div>
      <div class="stat-card amber">
        <div class="stat-value">$<?= number_format($result['shortfall_total'], 2) ?></div>
        <div class="stat-label">Total Shortfall</div>
      </div>
      <div class="stat-card red">
        <div class="stat-value"><?= $result['error_count'] ?></div>
        <div class="stat-label">Errors</div>
      </div>
    </div>
    <?php $download_url = portal_url('download.php?filename=' . urlencode($result['filename'])); ?>
    <a href="<?= htmlspecialchars($download_url) ?>"
       class="btn btn-success" target="_blank">
      ↓ Download Output File
    </a>
  </div>
  <script>
    // Auto-trigger download
    window.location.href = <?= json_encode($download_url) ?>;
  </script>
  <?php endif; ?>

  <div class="card">
    <div class="card-title">Upload Files</div>
    <form method="POST" enctype="multipart/form-data" id="recon-form">

      <div class="form-group">
        <label>1. Client Data Spreadsheet</label>
        <p class="text-muted mb-1" style="font-size:0.8rem">
          Your practice Excel file — Client Data.xlsx
        </p>
        <div class="drop-zone" id="excel-zone">
          <input type="file" name="excel_file" id="excel-input"
                 accept=".xlsx,.xls" required/>
          <div class="drop-icon">📊</div>
          <div class="drop-label">Click to select or drag and drop</div>
          <div class="drop-sub">Excel files only (.xlsx, .xls)</div>
        </div>
        <div class="file-tags" id="excel-tags"></div>
      </div>

      <div class="form-group">
        <label>2. Remittance Advice PDFs</label>
        <p class="text-muted mb-1" style="font-size:0.8rem">
          Select all remittance PDFs — you can pick multiple at once
        </p>
        <div class="drop-zone" id="pdf-zone">
          <input type="file" name="pdf_files[]" id="pdf-input"
                 accept=".pdf" multiple required/>
          <div class="drop-icon">📄</div>
          <div class="drop-label">Click to select or drag and drop</div>
          <div class="drop-sub">PDF files only — select multiple</div>
        </div>
        <div class="file-tags" id="pdf-tags"></div>
      </div>

      <button type="submit" class="btn btn-primary btn-lg" id="run-btn">
        ▶ Run Reconciliation
      </button>
      <div class="spinner" id="spinner">
        ⏳ Processing — please wait, this may take up to 60 seconds...
      </div>
    </form>
  </div>

  <div class="card">
    <div class="card-title">File Naming Guide</div>
    <p class="text-muted mb-2" style="font-size:0.84rem">
      Remittance PDFs must contain the medical aid name in the filename.
    </p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Medical Aid</th><th>Required keyword</th><th>Example</th></tr></thead>
        <tbody>
          <tr><td>Alliance Health</td><td><code>alliance</code></td><td>Alliance_March2026.pdf</td></tr>
          <tr><td>Bonvie</td><td><code>bonvie</code></td><td>Bonvie_Feb2026.pdf</td></tr>
          <tr><td>CellMed</td><td><code>cellmed</code></td><td>cellmed_Jul2025.pdf</td></tr>
          <tr><td>Cimas</td><td><code>cimas</code></td><td>Cimas_Mar2026.pdf</td></tr>
          <tr><td>FLIMAS</td><td><code>flimas</code></td><td>FLIMAS_Feb2026.pdf</td></tr>
          <tr><td>First Mutual Health</td><td><code>fmh</code></td><td>FMH_Jan2026.pdf</td></tr>
          <tr><td>PSMAS</td><td><code>psmas</code></td><td>PSMAS_Apr2026.pdf</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
  wireDropZone('excel-zone', 'excel-input', 'excel-tags', false);
  wireDropZone('pdf-zone',   'pdf-input',   'pdf-tags',   true);

  document.getElementById('recon-form').addEventListener('submit', () => {
    document.getElementById('run-btn').disabled = true;
    document.getElementById('spinner').classList.add('active');
  });
});
</script>

<?php require __DIR__ . '/includes/footer.php'; ?>