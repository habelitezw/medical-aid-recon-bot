<?php
require_once __DIR__ . '/auth.php';
session_init();
session_unset();
session_destroy();
header('Location: ' . portal_url('login.php'));
exit;
