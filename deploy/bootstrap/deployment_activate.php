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
    foreach (['app.py', 'vendor', 'index.php', 'scripts/run_migrations.py'] as $required_path) {
        if (!file_exists($release_path . '/' . $required_path)) {
            fail(400, 'Release package is incomplete.');
        }
    }
}

function run_command(array $command, string $working_directory, array $environment = []): array {
    if (!function_exists('proc_open')) {
        return [
            'exit_code' => 127,
            'stdout' => '',
            'stderr' => 'The PHP proc_open function is unavailable.',
        ];
    }

    $descriptor_spec = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];

    $process_environment = array_merge($_ENV, $environment);
    $process = @proc_open(
        $command,
        $descriptor_spec,
        $pipes,
        $working_directory,
        $process_environment,
        ['bypass_shell' => true]
    );

    if (!is_resource($process)) {
        return [
            'exit_code' => 127,
            'stdout' => '',
            'stderr' => 'Unable to start the migration process.',
        ];
    }

    fclose($pipes[0]);
    $stdout = stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    $stderr = stream_get_contents($pipes[2]);
    fclose($pipes[2]);

    return [
        'exit_code' => proc_close($process),
        'stdout' => trim((string) $stdout),
        'stderr' => trim((string) $stderr),
    ];
}

function run_release_migrations(string $release_id, array $environment = []): array {
    $release_path = root_path('releases/' . $release_id);
    $script_path = $release_path . '/scripts/run_migrations.py';
    $attempts = [];

    foreach (['python3', 'python'] as $python_binary) {
        $result = run_command([$python_binary, $script_path], $release_path, $environment);
        $attempts[] = [
            'python' => $python_binary,
            'exit_code' => $result['exit_code'],
            'stdout' => $result['stdout'],
            'stderr' => $result['stderr'],
        ];

        if ($result['exit_code'] === 0) {
            return [
                'ok' => true,
                'python' => $python_binary,
                'stdout' => $result['stdout'],
                'stderr' => $result['stderr'],
                'attempts' => $attempts,
            ];
        }
    }

    return [
        'ok' => false,
        'attempts' => $attempts,
    ];
}

function request_payload(): array {
    $content_type = strtolower(trim((string) ($_SERVER['CONTENT_TYPE'] ?? '')));
    if (($separator = strpos($content_type, ';')) !== false) {
        $content_type = trim(substr($content_type, 0, $separator));
    }

    if ($content_type === 'application/json') {
        $raw_body = file_get_contents('php://input');
        if ($raw_body === false || trim($raw_body) === '') {
            return [];
        }

        $decoded_body = json_decode($raw_body, true);
        if (!is_array($decoded_body)) {
            fail(400, 'Invalid JSON payload.');
        }

        return $decoded_body;
    }

    return $_POST;
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

$request = request_payload();
$action = $request['action'] ?? 'activate';
$current_release = read_release('.current-release');

if ($action === 'activate' || $action === 'migrate') {
    $release_id = $request['release'] ?? '';
    validate_release($release_id);

    if ($action === 'migrate') {
        $migration_environment = [];
        $bootstrap_test_user_password = $_SERVER['HTTP_X_BOOTSTRAP_TEST_USER_PASSWORD'] ?? '';
        if ($bootstrap_test_user_password !== '') {
            $migration_environment['BOOTSTRAP_TEST_USER_PASSWORD'] = $bootstrap_test_user_password;
        }

        $migration = run_release_migrations($release_id, $migration_environment);
        if (!$migration['ok']) {
            http_response_code(500);
            echo json_encode([
                'status' => 'error',
                'action' => $action,
                'release' => $release_id,
                'message' => 'Database migrations failed.',
                'attempts' => $migration['attempts'],
            ]);
            exit;
        }

        echo json_encode([
            'status' => 'ok',
            'action' => $action,
            'release' => $release_id,
            'python' => $migration['python'],
            'stdout' => $migration['stdout'],
            'stderr' => $migration['stderr'],
        ]);
        exit;
    }

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
