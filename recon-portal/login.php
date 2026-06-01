<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
session_init();

if (is_logged_in()) { header('Location: /dashboard.php'); exit; }

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email    = trim($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';

    if ($email && $password) {
        $res = api_call('/api/auth/login', 'POST',
                        ['email' => $email, 'password' => $password], false);
        if (isset($res['token'])) {
            $_SESSION['token'] = $res['token'];
            $_SESSION['user']  = $res['user'];
            header('Location: /dashboard.php');
            exit;
        } else {
            $error = $res['error'] ?? 'Login failed. Please try again.';
        }
    } else {
        $error = 'Please enter your email and password.';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sign In — <?= APP_NAME ?></title>
  <link rel="stylesheet" href="/deployment_asset.php?file=style.css"/>
</head>
<body>
<div class="login-wrap">
  <div class="login-card">
    <div class="login-brand">
      <div class="brand">Habelite</div>
      <div class="sub">Medical Aid Reconciliation Portal</div>
    </div>

    <?php if ($error): ?>
    <div class="alert alert-error"><?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <form method="POST">
      <div class="form-group">
        <label>Email Address</label>
        <input type="email" name="email" required autofocus
               value="<?= htmlspecialchars($_POST['email'] ?? '') ?>"/>
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" name="password" required/>
      </div>
      <button type="submit" class="btn btn-primary btn-block btn-lg">
        Sign In
      </button>
    </form>

    <p class="text-muted mt-2" style="text-align:center;font-size:0.78rem;">
      <?= APP_NAME ?> v<?= APP_VERSION ?> — Habelite
    </p>
  </div>
</div>
</body>
</html>
