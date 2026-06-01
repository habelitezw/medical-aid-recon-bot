<?php

require_once __DIR__ . '/deployment_release.php';

$allowed_files = [
    'index.php',
    'login.php',
    'logout.php',
    'dashboard.php',
    'run.php',
    'history.php',
    'codes.php',
    'users.php',
    'profile.php',
];

$filename = $_GET['file'] ?? '';
if (!in_array($filename, $allowed_files, true)) {
    http_response_code(404);
    exit('Not found');
}

try {
    require active_release_path() . '/' . $filename;
} catch (Throwable $error) {
    http_response_code(503);
    exit('Application release is unavailable.');
}
