<?php

function release_root(): string {
    return __DIR__;
}

function release_id_from_file(string $filename): string {
    $path = release_root() . '/' . $filename;
    if (!is_file($path)) {
        throw new RuntimeException('No active release is configured.');
    }

    $release_id = trim((string) file_get_contents($path));
    if (!preg_match('/\A[a-f0-9]{40}\z/', $release_id)) {
        throw new RuntimeException('The configured release is invalid.');
    }

    return $release_id;
}

function active_release_path(): string {
    $path = release_root() . '/releases/' . release_id_from_file('.current-release');
    if (!is_dir($path)) {
        throw new RuntimeException('The active release directory does not exist.');
    }

    return $path;
}
