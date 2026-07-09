<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
session_init();

if (is_logged_in()) { header('Location: ' . portal_url('dashboard.php')); exit; }

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
            header('Location: ' . portal_url('dashboard.php'));
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
  <title>Sign In - <?= APP_NAME ?></title>
  <link rel="stylesheet" href="<?= htmlspecialchars(asset_url('style.css')) ?>"/>
</head>
<body>
<div class="login-wrap">
  <div class="login-card">
    <div class="login-brand">
      <div class="brand">Optex</div>
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
        <div class="password-field">
          <input type="password" name="password" id="password" required
                 autocomplete="current-password"/>
          <button type="button" class="password-toggle" id="toggle-password"
                  aria-label="Show password" aria-pressed="false" style="display: flex; align-items: center; justify-content: center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          </button>
        </div>
      </div>
      <button type="submit" class="btn btn-primary btn-block btn-lg">
        Sign In
      </button>
    </form>

    <p class="text-muted mt-2" style="text-align:center;font-size:0.78rem;">
      <?= APP_NAME ?> v<?= APP_VERSION ?>
    </p>
  </div>
</div>

<script>
(function () {
  const passwordInput = document.getElementById('password');
  const toggleButton = document.getElementById('toggle-password');
  if (!passwordInput || !toggleButton) return;

  const eyeOpenSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
  
  const eyeClosedSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;

  toggleButton.addEventListener('click', function () {
    const shouldShow = passwordInput.type === 'password';
    passwordInput.type = shouldShow ? 'text' : 'password';
    toggleButton.innerHTML = shouldShow ? eyeClosedSvg : eyeOpenSvg;
    toggleButton.setAttribute('aria-label', shouldShow ? 'Hide password' : 'Show password');
    toggleButton.setAttribute('aria-pressed', shouldShow ? 'true' : 'false');
  });
})();
</script>
</script>
</body>
</html>
