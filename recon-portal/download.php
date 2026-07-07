<?php
set_time_limit(300);
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_login();

$filename = $_GET['filename'] ?? '';
if (!$filename) {
    die("Filename is required.");
}

// 1. Sanitize the filename to prevent directory traversal and restrict to expected patterns
$filename = basename($filename);
if (!preg_match('/^RECON_\d{8}_\d{6}_[a-zA-Z0-9_]+\.xlsx$/i', $filename)) {
    die("Invalid filename format.");
}

// 2. Resolve the path to the recon_outputs directory
$output_dir = getenv('RECON_OUTPUT_DIR');
if ($output_dir === false || $output_dir === '') {
    $output_dir = __DIR__ . '/../recon_outputs';
}

$filepath = rtrim($output_dir, '/') . '/' . $filename;

// 3. Verify the file exists on disk
if (!file_exists($filepath)) {
    die("File not found on disk: " . htmlspecialchars($filename));
}

// 4. Send correct headers for Excel spreadsheet download
header('Content-Description: File Transfer');
header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
header('Content-Disposition: attachment; filename="' . basename($filepath) . '"');
header('Expires: 0');
header('Cache-Control: must-revalidate');
header('Pragma: public');
header('Content-Length: ' . filesize($filepath));

// Clean any output buffers to prevent file corruption
if (ob_get_level()) {
    ob_end_clean();
}
flush();

// 5. Stream the file directly
readfile($filepath);
exit;
