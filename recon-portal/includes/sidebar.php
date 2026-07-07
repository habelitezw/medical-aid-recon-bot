<?php
// =============================================================
// includes/sidebar.php
// =============================================================
$user     = get_user();
$is_admin = is_admin();
$current  = basename($_SERVER['PHP_SELF']);
?>
<aside class="sidebar">
  <div class="sidebar-brand">
    <div class="brand-name">Optex</div>
    <div class="brand-sub">Medical Aid Recon</div>
  </div>

  <nav class="sidebar-nav">
    <a href="<?= htmlspecialchars(portal_url('dashboard.php')) ?>"
       class="nav-item <?= $current === 'dashboard.php' ? 'active' : '' ?>">
      <span class="nav-icon">⊞</span> Dashboard
    </a>
    <a href="<?= htmlspecialchars(portal_url('run.php')) ?>"
       class="nav-item <?= $current === 'run.php' ? 'active' : '' ?>">
      <span class="nav-icon">▶</span> Run Reconciliation
    </a>
    <a href="<?= htmlspecialchars(portal_url('history.php')) ?>"
       class="nav-item <?= $current === 'history.php' ? 'active' : '' ?>">
      <span class="nav-icon">☰</span> History
    </a>

    <?php if ($is_admin): ?>
    <div class="nav-section">Admin</div>
    <a href="<?= htmlspecialchars(portal_url('codes.php')) ?>"
       class="nav-item <?= $current === 'codes.php' ? 'active' : '' ?>">
      <span class="nav-icon">⚙</span> Reason Codes
    </a>
    <a href="<?= htmlspecialchars(portal_url('users.php')) ?>"
       class="nav-item <?= $current === 'users.php' ? 'active' : '' ?>">
      <span class="nav-icon">👤</span> Users
    </a>
    <?php endif; ?>
  </nav>

  <div class="sidebar-footer">
    <a href="<?= htmlspecialchars(portal_url('profile.php')) ?>" class="nav-item">
      <span class="nav-icon">◎</span>
      <?= htmlspecialchars($user['name'] ?? 'Profile') ?>
    </a>
    <a href="<?= htmlspecialchars(portal_url('logout.php')) ?>" class="nav-item nav-logout">
      <span class="nav-icon">→</span> Sign Out
    </a>
  </div>
</aside>
