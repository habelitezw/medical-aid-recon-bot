<?php
// =============================================================
// config.php — Central configuration
// cPanel deploys can override values in config.local.php
// =============================================================

$portal_config_overrides = [];
$portal_local_config     = __DIR__ . '/config.local.php';

if (is_file($portal_local_config)) {
    $loaded = require $portal_local_config;
    if (is_array($loaded)) {
        $portal_config_overrides = $loaded;
    }
}

function portal_config_value(string $key, mixed $default): mixed {
    global $portal_config_overrides;

    $env = getenv($key);
    if ($env !== false && $env !== '') {
        return $env;
    }

    return $portal_config_overrides[$key] ?? $default;
}

function portal_default_api_base_url(): string {
    $host = $_SERVER['HTTP_HOST'] ?? '127.0.0.1:8000';

    if (str_contains($host, '127.0.0.1') || str_contains($host, 'localhost')) {
        return 'http://127.0.0.1:5000';
    }

    $configured = getenv('PORTAL_DEFAULT_API_BASE_URL');
    if ($configured !== false && $configured !== '') {
        return rtrim($configured, '/');
    }

    return 'https://habe.co.zw/myclients/medical-aid-recon-bot-api';
}

define('API_BASE_URL', rtrim((string) portal_config_value('API_BASE_URL', portal_default_api_base_url()), '/'));
define('APP_NAME', (string) portal_config_value('APP_NAME', 'Medical Aid Reconciliation'));
define('APP_VERSION', (string) portal_config_value('APP_VERSION', '2.0'));
define('SESSION_NAME', (string) portal_config_value('SESSION_NAME', 'recon_session'));
define('SESSION_LIFETIME', (int) portal_config_value('SESSION_LIFETIME', 28800));
