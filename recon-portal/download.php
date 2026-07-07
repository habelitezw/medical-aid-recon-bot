<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_login();

$run_id = $_GET['run_id'] ?? '';
if (!$run_id) {
    die("Run ID is required.");
}

$url = API_BASE_URL . "/api/history/" . urlencode($run_id) . "/download";
$ch  = curl_init($url);

$headers = [
    'Authorization: Bearer ' . get_token(),
];

$response_headers = [];

curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 180,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_HTTPHEADER     => $headers,
    CURLOPT_CUSTOMREQUEST  => 'GET',
    CURLOPT_HEADERFUNCTION => function($ch, $header_line) use (&$response_headers) {
        $len = strlen($header_line);
        $parts = explode(':', $header_line, 2);
        if (count($parts) === 2) {
            $key = strtolower(trim($parts[0]));
            $value = trim($parts[1]);
            $response_headers[$key] = $value;
        }
        return $len;
    }
]);

$body   = curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$err    = curl_error($ch);
curl_close($ch);

if ($err) {
    die("Download error: " . htmlspecialchars($err));
}

// If the API returned a redirect, forward the redirect to the client browser
if ($status === 301 || $status === 302 || $status === 307 || $status === 308) {
    if (isset($response_headers['location'])) {
        header("Location: " . $response_headers['location']);
        exit;
    }
}

if ($status !== 200) {
    $decoded = json_decode($body, true);
    $error_msg = $decoded['error'] ?? 'Failed to download file.';
    die("Error ($status): " . htmlspecialchars($error_msg));
}

// Forward content type
if (isset($response_headers['content-type'])) {
    header("Content-Type: " . $response_headers['content-type']);
} else {
    header("Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
}

// Forward content disposition
if (isset($response_headers['content-disposition'])) {
    header("Content-Disposition: " . $response_headers['content-disposition']);
} else {
    header("Content-Disposition: attachment; filename=\"recon_output.xlsx\"");
}

// Forward content length if available
if (isset($response_headers['content-length'])) {
    header("Content-Length: " . $response_headers['content-length']);
}

// Clean any previous output buffering to avoid output corruption
if (ob_get_level()) {
    ob_end_clean();
}

echo $body;
exit;
