<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_login();

$page_title = 'Run History';

// Handle download redirect
if (isset($_GET['download'])) {
    $run_id = $_GET['download'];
    $res    = api_call("/api/history/{$run_id}/download");
    if (isset($res['download_url'])) {
        header('Location: ' . $res['download_url']);
        exit;
    }
}

$history = api_call('/api/history');
$runs    = $history['runs'] ?? [];
?>
<?php require __DIR__ . '/includes/header.php'; ?>
<?php require __DIR__ . '/includes/sidebar.php'; ?>

<div class="main-content">
  <div class="page-header">
    <h1>☰ Reconciliation History</h1>
    <p>All past reconciliation runs<?= !is_admin() ? ' for your account' : '' ?>.</p>
  </div>

  <div class="card">
    <div class="card-title">
      <?= count($runs) ?> run<?= count($runs) !== 1 ? 's' : '' ?> found
    </div>
    <?php if (empty($runs)): ?>
      <p class="text-muted">No runs yet. <a href="<?= htmlspecialchars(portal_url('run.php')) ?>">Run your first reconciliation →</a></p>
    <?php else: ?>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date &amp; Time</th>
            <?php if (is_admin()): ?><th>Run By</th><?php endif; ?>
            <th>PDFs</th>
            <th>Excel Claims</th>
            <th>Matched</th>
            <th>Shortfall (USD)</th>
            <th>Errors</th>
            <th>Output File</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($runs as $run): ?>
          <tr>
            <td><?= date('d M Y H:i', strtotime($run['run_date'])) ?></td>
            <?php if (is_admin()): ?>
            <td><?= htmlspecialchars($run['users']['name'] ?? '—') ?></td>
            <?php endif; ?>
            <td><?= $run['pdf_count'] ?></td>
            <td><?= $run['excel_claims'] ?></td>
            <td><?= $run['matched_count'] ?></td>
            <td>$<?= number_format($run['shortfall_total_usd'], 2) ?></td>
            <td>
              <?php if ($run['error_count'] > 0): ?>
              <span class="badge badge-error"><?= $run['error_count'] ?></span>
              <?php else: ?>
              <span class="text-muted">—</span>
              <?php endif; ?>
            </td>
            <td style="font-size:0.78rem;color:var(--text-muted)">
              <?= htmlspecialchars($run['output_filename']) ?>
            </td>
            <td>
              <a href="<?= htmlspecialchars(portal_url('history.php?download=' . urlencode($run['id']))) ?>"
                 class="btn btn-outline btn-sm">↓ Download</a>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
    <?php endif; ?>
  </div>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
