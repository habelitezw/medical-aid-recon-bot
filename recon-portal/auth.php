<?php
// =============================================================
// auth.php — Session and API call helpers
// =============================================================

require_once __DIR__ . '/config.php';

function portal_base_path(): string {
    $script_name = $_SERVER['SCRIPT_NAME'] ?? '';
    $base_path = str_replace('\\', '/', dirname($script_name));
    $base_path = rtrim($base_path, '/');

    if ($base_path === '' || $base_path === '.') {
        return '';
    }

    return $base_path === '/' ? '' : $base_path;
}

function portal_url(string $path = ''): string {
    $base_path = portal_base_path();
    $path = ltrim($path, '/');

    if ($path === '') {
        return $base_path === '' ? '/' : $base_path . '/';
    }

    return ($base_path === '' ? '' : $base_path) . '/' . $path;
}

function asset_url(string $file): string {
    $document_root = rtrim(str_replace('\\', '/', $_SERVER['DOCUMENT_ROOT'] ?? ''), '/');

    if ($document_root !== '' && is_file($document_root . '/deployment_asset.php')) {
        return portal_url('deployment_asset.php?file=' . rawurlencode($file));
    }

    return portal_url('assets/' . rawurlencode($file));
}

function session_init() {
    if (session_status() === PHP_SESSION_NONE) {
        session_name(SESSION_NAME);
        session_set_cookie_params([
            'lifetime' => SESSION_LIFETIME,
            'path'     => portal_base_path() ?: '/',
            'secure'   => isset($_SERVER['HTTPS']),
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
        session_start();
    }
}

function is_logged_in(): bool {
    session_init();
    return isset($_SESSION['token']) && isset($_SESSION['user']);
}

function require_login() {
    if (!is_logged_in()) {
        header('Location: ' . portal_url('login.php'));
        exit;
    }
}

function require_admin() {
    require_login();
    if ($_SESSION['user']['role'] !== 'admin') {
        header('Location: ' . portal_url('dashboard.php?error=access_denied'));
        exit;
    }
}

function get_token(): string {
    return $_SESSION['token'] ?? '';
}

function get_user(): array {
    return $_SESSION['user'] ?? [];
}

function is_admin(): bool {
    return (get_user()['role'] ?? '') === 'admin';
}

// =============================================================
// API caller — all HTTP methods
// =============================================================

function api_call(string $endpoint, string $method = 'GET',
                  array $data = [], bool $auth = true): array {
    $url = API_BASE_URL . $endpoint;
    $ch  = curl_init($url);

    $headers = ['Content-Type: application/json', 'Accept: application/json'];
    if ($auth && is_logged_in()) {
        $headers[] = 'Authorization: Bearer ' . get_token();
    }

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 120,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_CUSTOMREQUEST  => $method,
    ]);

    if (in_array($method, ['POST', 'PUT', 'PATCH']) && !empty($data)) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    }

    $body    = curl_exec($ch);
    $status  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err     = curl_error($ch);
    curl_close($ch);

    if ($err) {
        return ['error' => 'Connection error: ' . $err, '_status' => 0];
    }

    $decoded = json_decode($body, true) ?? ['raw' => $body];
    $decoded['_status'] = $status;
    return $decoded;
}

function api_upload(string $endpoint, array $files, array $fields = []): array {
    $url  = API_BASE_URL . $endpoint;
    $ch   = curl_init($url);
    $post = [];

    foreach ($fields as $key => $value) {
        $post[$key] = $value;
    }

    // Excel file
    if (isset($files['excel_file']) && $files['excel_file']['error'] === 0) {
        $post['excel_file'] = new CURLFile(
            $files['excel_file']['tmp_name'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            $files['excel_file']['name']
        );
    }

    // Multiple PDF files
    if (isset($files['pdf_files'])) {
        $pdfs = $files['pdf_files'];
        // Normalise single vs multiple file uploads
        if (!is_array($pdfs['name'])) {
            $pdfs = array_map(fn($v) => [$v], $pdfs);
        }
        $count = count($pdfs['name']);
        for ($i = 0; $i < $count; $i++) {
            if ($pdfs['error'][$i] === 0) {
                $post["pdf_files[$i]"] = new CURLFile(
                    $pdfs['tmp_name'][$i],
                    'application/pdf',
                    $pdfs['name'][$i]
                );
            }
        }
    }

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 180,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $post,
        CURLOPT_HTTPHEADER     => [
            'Authorization: Bearer ' . get_token(),
            'Accept: application/json',
        ],
    ]);

    $body   = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err    = curl_error($ch);
    curl_close($ch);

    if ($err) {
        return ['error' => 'Upload error: ' . $err, '_status' => 0];
    }

    $decoded = json_decode($body, true) ?? ['raw' => $body];
    $decoded['_status'] = $status;
    return $decoded;
}
