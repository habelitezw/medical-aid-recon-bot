<?php

header('Content-Type: application/json');

function fail(int $status, string $message): void {
    http_response_code($status);
    echo json_encode(['status' => 'error', 'message' => $message]);
    exit;
}

function root_path(string $filename = ''): string {
    $root = __DIR__;
    return $filename === '' ? $root : $root . '/' . $filename;
}

function read_release(string $filename): string {
    $path = root_path($filename);
    return is_file($path) ? trim((string) file_get_contents($path)) : '';
}

function write_release(string $filename, string $release_id): void {
    $path = root_path($filename);
    $temporary_path = $path . '.tmp';

    if (file_put_contents($temporary_path, $release_id . PHP_EOL, LOCK_EX) === false ||
        !rename($temporary_path, $path)) {
        fail(500, 'Unable to update the active release.');
    }
}

function validate_release(string $release_id): void {
    if (!preg_match('/\A[a-f0-9]{40}\z/', $release_id)) {
        fail(400, 'Invalid release identifier.');
    }

    $release_path = root_path('releases/' . $release_id);
    foreach (['app.py', 'vendor', 'index.php'] as $required_path) {
        if (!file_exists($release_path . '/' . $required_path)) {
            fail(400, 'Release package is incomplete.');
        }
    }
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    fail(405, 'Method not allowed.');
}

$secret_path = root_path('deployment_secret.php');
$expected_token = is_file($secret_path) ? (string) require $secret_path : '';
$provided_token = $_SERVER['HTTP_X_DEPLOYMENT_TOKEN'] ?? '';
if ($expected_token === '' || !hash_equals($expected_token, $provided_token)) {
    fail(403, 'Forbidden.');
}

$action = $_POST['action'] ?? 'activate';
$current_release = read_release('.current-release');

if ($action === 'activate') {
    $release_id = $_POST['release'] ?? '';
    validate_release($release_id);

    if ($current_release !== '' && $current_release !== $release_id) {
        write_release('.previous-release', $current_release);
    }
} elseif ($action === 'rollback') {
    $release_id = read_release('.previous-release');
    validate_release($release_id);

    if ($current_release !== '') {
        write_release('.previous-release', $current_release);
    }
} else {
    fail(400, 'Invalid deployment action.');
}

write_release('.current-release', $release_id);

$restart_directory = root_path('tmp');
if (!is_dir($restart_directory) && !mkdir($restart_directory, 0755, true)) {
    fail(500, 'Unable to create the Passenger restart directory.');
}
if (file_put_contents($restart_directory . '/restart.txt', $release_id . PHP_EOL, LOCK_EX) === false) {
    fail(500, 'Unable to restart Passenger.');
}

echo json_encode([
    'status'   => 'ok',
    'action'   => $action,
    'release'  => $release_id,
    'previous' => $current_release,
]);
