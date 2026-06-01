<?php

require_once __DIR__ . '/deployment_release.php';

$assets = [
    'app.js'    => ['application/javascript; charset=UTF-8', 'assets/app.js'],
    'style.css' => ['text/css; charset=UTF-8', 'assets/style.css'],
];

$filename = $_GET['file'] ?? '';
if (!isset($assets[$filename])) {
    http_response_code(404);
    exit('Not found');
}

try {
    [$content_type, $relative_path] = $assets[$filename];
    $path = active_release_path() . '/' . $relative_path;
    if (!is_file($path)) {
        throw new RuntimeException('Asset is unavailable.');
    }

    header('Content-Type: ' . $content_type);
    header('Cache-Control: no-cache');
    readfile($path);
} catch (Throwable $error) {
    http_response_code(503);
    exit('Application asset is unavailable.');
}
