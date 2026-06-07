<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
session_init();
if (is_logged_in()) {
    header('Location: ' . portal_url('dashboard.php'));
} else {
    header('Location: ' . portal_url('login.php'));
}
exit;
