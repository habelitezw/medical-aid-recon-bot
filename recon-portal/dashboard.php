<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_login();

$page_title = 'Dashboard';
$user       = get_user();

// Fetch recent runs
$history = api_call('/api/history');
$runs    = $history['runs'] ?? [];

// Compute summary stats from recent runs
$total_runs       = count($runs);
$total_shortfall  = array_sum(array_column($runs, 'shortfall_total_usd'));
$total_matched    = array_sum(array_column($runs, 'matched_count'));
$total_errors     = array_sum(array_column($runs, 'error_count'));
$recent_runs      = array_slice($runs, 0, 5);
?>
<?php require __DIR__ . '/includes/header.php'; ?>
<?php require __DIR__ . '/includes/sidebar.php'; ?>

<div class="main-content">
  <div class="page-header">
    <h1>Welcome back, <?= htmlspecialchars($user['name']) ?></h1>
    <p>Medical Aid Reconciliation Portal — Overview</p>
  </div>

  <div class="stat-grid">
    <div class="stat-card blue">
      <div class="stat-value"><?= $total_runs ?></div>
      <div class="stat-label">Total Runs</div>
    </div>
    <div class="stat-card green">
      <div class="stat-value"><?= $total_matched ?></div>
      <div class="stat-label">Claims Matched</div>
    </div>
    <div class="stat-card amber">
      <div class="stat-value">$<?= number_format($total_shortfall, 2) ?></div>
      <div class="stat-label">Total Shortfall (USD)</div>
    </div>
    <div class="stat-card red">
      <div class="stat-value"><?= $total_errors ?></div>
      <div class="stat-label">Processing Errors</div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Recent Reconciliation Runs</div>
    <?php if (empty($recent_runs)): ?>
      <p class="text-muted">No reconciliation runs yet.
        <a href="/run.php">Run your first reconciliation →</a>
      </p>
    <?php else: ?>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Run By</th>
            <th>PDFs</th>
            <th>Claims</th>
            <th>Matched</th>
            <th>Shortfall (USD)</th>
            <th>Errors</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($recent_runs as $run): ?>
          <tr>
            <td><?= date('d M Y H:i', strtotime($run['run_date'])) ?></td>
            <td><?= htmlspecialchars($run['users']['name'] ?? 'Unknown') ?></td>
            <td><?= $run['pdf_count'] ?></td>
            <td><?= $run['excel_claims'] ?></td>
            <td><?= $run['matched_count'] ?></td>
            <td>$<?= number_format($run['shortfall_total_usd'], 2) ?></td>
            <td><?= $run['error_count'] ?></td>
            <td>
              <a href="/history.php?download=<?= urlencode($run['id']) ?>"
                 class="btn btn-outline btn-sm">Download</a>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
    <div class="mt-2">
      <a href="/history.php" class="btn btn-secondary btn-sm">View All History →</a>
    </div>
    <?php endif; ?>
  </div>

  <div class="card">
    <div class="card-title">Quick Actions</div>
    <div class="flex gap-2">
      <a href="/run.php"     class="btn btn-primary">▶ New Reconciliation</a>
      <a href="/history.php" class="btn btn-outline">☰ View History</a>
      <?php if (is_admin()): ?>
      <a href="/codes.php"   class="btn btn-outline">⚙ Manage Reason Codes</a>
      <a href="/users.php"   class="btn btn-outline">👤 Manage Users</a>
      <?php endif; ?>
    </div>
  </div>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>