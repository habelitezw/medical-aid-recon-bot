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

function read_release_environment(string $release_path): array {
    $environment_path = $release_path . '/.env';
    if (!is_file($environment_path)) {
        return [];
    }

    $lines = @file($environment_path, FILE_IGNORE_NEW_LINES);
    if ($lines === false) {
        return [];
    }

    $values = [];
    foreach ($lines as $raw_line) {
        $line = trim($raw_line);
        if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) {
            continue;
        }

        [$key, $value] = explode('=', $line, 2);
        $values[trim($key)] = trim($value, " \	\n\r\0\x0B\"'");
    }

    return $values;
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

function append_python_candidate(array &$candidates, string $candidate): void {
    $candidate = trim($candidate);
    if ($candidate === '' || in_array($candidate, $candidates, true)) {
        return;
    }

    $candidates[] = $candidate;
}

function append_python_candidate_matches(array &$candidates, string $pattern): void {
    if ($pattern === '') {
        return;
    }

    $matches = glob($pattern);
    if ($matches === false) {
        return;
    }

    sort($matches, SORT_NATURAL);
    foreach ($matches as $match) {
        if (is_file($match) && is_executable($match)) {
            append_python_candidate($candidates, $match);
        }
    }
}

function detect_passenger_python(): array {
    $bootstrap_wsgi = root_path('passenger_wsgi.py');
    $result = run_command(['ps', '-eo', 'pid=,args='], root_path());
    if ($result['exit_code'] !== 0 || $result['stdout'] === '') {
        return [];
    }

    $candidates = [];
    foreach (preg_split('/\\r?\\n/', $result['stdout']) as $line) {
        $line = trim($line);
        if ($line === '') {
            continue;
        }

        if (strpos($line, $bootstrap_wsgi) === false && strpos($line, 'passenger_wsgi.py') === false) {
            continue;
        }

        if (!preg_match('/^(\d+)\s+(.*)$/', $line, $matches)) {
            continue;
        }

        $pid = $matches[1];
        $command = trim($matches[2]);
        $parts = preg_split('/\s+/', $command);
        $first = $parts[0] ?? '';
        if ($first !== '' && $first[0] === '/' && is_file($first)) {
            append_python_candidate($candidates, $first);
        }

        $proc_exe = '/proc/' . $pid . '/exe';
        if (is_link($proc_exe)) {
            $resolved = @readlink($proc_exe);
            if (is_string($resolved) && $resolved !== '') {
                append_python_candidate($candidates, $resolved);
            }
        }
    }

    return $candidates;
}

function detect_cpanel_python(): array {
    $candidates = [];
    $environment_keys = ['VIRTUAL_ENV', 'OPENSHIFT_PYTHON_DIR', 'PYTHON_HOME', 'PYTHONHOME'];

    foreach ($environment_keys as $key) {
        $value = trim((string) ($_ENV[$key] ?? $_SERVER[$key] ?? ''));
        if ($value === '') {
            continue;
        }

        if (is_dir($value)) {
            append_python_candidate($candidates, $value . '/bin/python');
            append_python_candidate($candidates, $value . '/bin/python3');
        } else {
            append_python_candidate($candidates, $value);
        }
    }

    $home = trim((string) ($_ENV['HOME'] ?? $_SERVER['HOME'] ?? ''));
    $root = root_path();
    $real_root = realpath($root);
    $real_home = $home !== '' ? realpath($home) : false;
    if ($real_root !== false && $real_home !== false) {
        $root_relative_to_home = ltrim(str_replace($real_home, '', $real_root), '/');
        if ($root_relative_to_home !== '' && strpos($root_relative_to_home, '..') === false) {
            append_python_candidate_matches(
                $candidates,
                $real_home . '/virtualenv/' . $root_relative_to_home . '/*/bin/python*'
            );
        }

        append_python_candidate_matches(
            $candidates,
            $real_home . '/virtualenv/*/*/bin/python*'
        );
    }

    return $candidates;
}

function python_candidates(string $release_path): array {
    $release_environment = read_release_environment($release_path);
    $candidates = [];

    append_python_candidate($candidates, $release_environment['PYTHON_BIN'] ?? '');
    append_python_candidate($candidates, $_ENV['PYTHON_BIN'] ?? '');
    append_python_candidate($candidates, $_SERVER['PYTHON_BIN'] ?? '');

    foreach (detect_passenger_python() as $candidate) {
        append_python_candidate($candidates, $candidate);
    }

    foreach (detect_cpanel_python() as $candidate) {
        append_python_candidate($candidates, $candidate);
    }

    append_python_candidate($candidates, 'python3');
    append_python_candidate($candidates, 'python');

    return $candidates;
}

function detect_python_version(string $python_binary, string $working_directory, array $environment = []): array {
    $result = run_command(
        [
            $python_binary,
            '-c',
            'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))',
        ],
        $working_directory,
        $environment
    );

    $version = trim($result['stdout']);
    if (!preg_match('/^\d+\.\d+\.\d+$/', $version)) {
        $version = '';
    }

    return [
        'exit_code' => $result['exit_code'],
        'stdout' => $result['stdout'],
        'stderr' => $result['stderr'],
        'version' => $version,
    ];
}

function python_version_supported(string $version): bool {
    if (!preg_match('/^(\d+)\.(\d+)\.(\d+)$/', $version, $matches)) {
        return false;
    }

    $major = (int) $matches[1];
    $minor = (int) $matches[2];
    return $major > 3 || ($major === 3 && $minor >= 11);
}

function run_release_migrations(string $release_id, array $environment = []): array {
    $release_path = root_path('releases/' . $release_id);
    $script_path = $release_path . '/scripts/run_migrations.py';
    $attempts = [];

    foreach (python_candidates($release_path) as $python_binary) {
        $version_check = detect_python_version($python_binary, $release_path, $environment);
        if ($version_check['exit_code'] !== 0) {
            $attempts[] = [
                'python' => $python_binary,
                'version' => $version_check['version'],
                'exit_code' => $version_check['exit_code'],
                'stdout' => $version_check['stdout'],
                'stderr' => $version_check['stderr'],
            ];
            continue;
        }

        if (!python_version_supported($version_check['version'])) {
            $attempts[] = [
                'python' => $python_binary,
                'version' => $version_check['version'],
                'exit_code' => 126,
                'stdout' => '',
                'stderr' => sprintf(
                    'Python 3.11+ is required for this release. Found %s. Configure PYTHON_BIN or ensure Passenger is running with a supported interpreter.',
                    $version_check['version'] === '' ? 'an unknown version' : $version_check['version']
                ),
            ];
            continue;
        }
        $result = run_command([$python_binary, $script_path], $release_path, $environment);
        $attempts[] = [
            'python' => $python_binary,
            'version' => $version_check['version'],
            'exit_code' => $result['exit_code'],
            'stdout' => $result['stdout'],
            'stderr' => $result['stderr'],
        ];

        if ($result['exit_code'] === 0) {
            return [
                'ok' => true,
                'python' => $python_binary,
                'version' => $version_check['version'],
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
            'python_version' => $migration['version'],
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
