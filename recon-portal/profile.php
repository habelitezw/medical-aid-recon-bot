<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_login();

$page_title = 'My Profile';
$user       = get_user();
$message    = '';
$error      = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $current = $_POST['current_password'] ?? '';
    $new     = $_POST['new_password']     ?? '';
    $confirm = $_POST['confirm_password'] ?? '';

    if ($new !== $confirm) {
        $error = 'New passwords do not match.';
    } elseif (strlen($new) < 8) {
        $error = 'Password must be at least 8 characters.';
    } else {
        $res = api_call('/api/auth/change-password', 'POST', [
            'current_password' => $current,
            'new_password'     => $new,
        ]);
        $message = $res['message'] ?? '';
        $error   = $res['error']   ?? '';
    }
}
?>
<?php require __DIR__ . '/includes/header.php'; ?>
<?php require __DIR__ . '/includes/sidebar.php'; ?>

<div class="main-content">
  <div class="page-header">
    <h1>◎ My Profile</h1>
    <p>View your account details and change your password.</p>
  </div>

  <div class="card" style="max-width:500px">
    <div class="card-title">Account Details</div>
    <table style="width:100%">
      <tr><td style="color:var(--text-muted);width:120px">Name</td>
          <td><?= htmlspecialchars($user['name']) ?></td></tr>
      <tr><td style="color:var(--text-muted)">Email</td>
          <td><?= htmlspecialchars($user['email']) ?></td></tr>
      <tr><td style="color:var(--text-muted)">Role</td>
          <td><span class="badge badge-<?= $user['role'] ?>"><?= $user['role'] ?></span></td></tr>
    </table>
  </div>

  <div class="card" style="max-width:500px">
    <div class="card-title">Change Password</div>

    <?php if ($message): ?>
    <div class="alert alert-success" data-auto-dismiss>✓ <?= htmlspecialchars($message) ?></div>
    <?php endif; ?>
    <?php if ($error): ?>
    <div class="alert alert-error">⚠ <?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <form method="POST">
      <div class="form-group">
        <label>Current Password *</label>
        <input type="password" name="current_password" required/>
      </div>
      <div class="form-group">
        <label>New Password * (minimum 8 characters)</label>
        <input type="password" name="new_password" required minlength="8"/>
      </div>
      <div class="form-group">
        <label>Confirm New Password *</label>
        <input type="password" name="confirm_password" required minlength="8"/>
      </div>
      <button type="submit" class="btn btn-primary">Update Password</button>
    </form>
  </div>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>