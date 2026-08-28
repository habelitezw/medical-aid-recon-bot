<?php
// =============================================================
// includes/sidebar.php
// =============================================================
$user     = get_user();
$is_admin = is_admin();
$current  = basename($_SERVER['PHP_SELF']);
?>
<aside class="sidebar">
  <div class="sidebar-brand" style="display: flex; align-items: center; gap: 12px;">
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; color: var(--light-blue);">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
        <line x1="8" y1="21" x2="16" y2="21"></line>
        <line x1="12" y1="17" x2="12" y2="21"></line>
      </svg>
      <div style="display: flex; flex-direction: column;">
        <div class="brand-name" style="font-size: 1rem; line-height: 1.1;">Optex</div>
        <div class="brand-sub" style="font-size: 0.65rem; margin-top: 2px;">Medical Aid Recon</div>
      </div>
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
