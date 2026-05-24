<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
session_init();
session_destroy();
header('Location: /login.php');
exit;