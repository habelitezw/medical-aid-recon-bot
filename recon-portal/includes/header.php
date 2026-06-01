<?php
// =============================================================
// includes/header.php
// =============================================================
$page_title = $page_title ?? APP_NAME;
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title><?= htmlspecialchars($page_title) ?> — <?= APP_NAME ?></title>
  <link rel="stylesheet" href="/deployment_asset.php?file=style.css"/>
</head>
<body>
<div class="app-layout">
