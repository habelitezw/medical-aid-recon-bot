<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_admin();

$page_title = 'Reason Code Manager';
$message    = '';
$error      = '';

$medical_aids = [
    'ALL', 'Alliance Health', 'Bonvie', 'CellMed',
    'Cimas', 'FLIMAS', 'First Mutual Health', 'PSMAS'
];

$classifications = [
    'Tariff difference',
    'Benefit exhausted',
    'Not a covered benefit',
    'Data / submission error',
    'Duplicate / submission error',
    'Scheme exclusion / co-payment',
    'Unclassified shortfall',
];

// Handle form actions
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'add') {
        $res = api_call('/api/codes', 'POST', [
            'code'           => $_POST['code'] ?? '',
            'medical_aid'    => $_POST['medical_aid'] ?? 'ALL',
            'description'    => $_POST['description'] ?? '',
            'classification' => $_POST['classification'] ?? '',
            'action'         => $_POST['action_text'] ?? '',
        ]);
        $message = $res['message'] ?? '';
        $error   = $res['error']   ?? '';

    } elseif ($action === 'edit') {
        $res = api_call('/api/codes/' . ($_POST['code_id'] ?? ''), 'PUT', [
            'code'           => $_POST['code'] ?? '',
            'medical_aid'    => $_POST['medical_aid'] ?? 'ALL',
            'description'    => $_POST['description'] ?? '',
            'classification' => $_POST['classification'] ?? '',
            'action'         => $_POST['action_text'] ?? '',
        ]);
        $message = $res['message'] ?? '';
        $error   = $res['error']   ?? '';

    } elseif ($action === 'delete') {
        $res     = api_call('/api/codes/' . ($_POST['code_id'] ?? ''), 'DELETE');
        $message = $res['message'] ?? '';
        $error   = $res['error']   ?? '';
    }
}

$codes_res = api_call('/api/codes');
$codes     = $codes_res['codes'] ?? [];

function badge_class(string $cls): string {
    if (str_contains($cls, 'ariff'))    return 'badge-tariff';
    if (str_contains($cls, 'xhaust'))   return 'badge-benefit';
    if (str_contains($cls, 'covered'))  return 'badge-covered';
    if (str_contains($cls, 'error'))    return 'badge-error';
    if (str_contains($cls, 'uplicate')) return 'badge-error';
    return 'badge-other';
}
?>
<?php require __DIR__ . '/includes/header.php'; ?>
<?php require __DIR__ . '/includes/sidebar.php'; ?>

<div class="main-content">
  <div class="page-header">
    <h1>⚙ Reason Code Manager</h1>
    <p>Configure shortfall reason codes for each medical aid.
       These codes appear on remittance advice and determine the action required.</p>
  </div>

  <?php if ($message): ?>
  <div class="alert alert-success" data-auto-dismiss>✓ <?= htmlspecialchars($message) ?></div>
  <?php endif; ?>
  <?php if ($error): ?>
  <div class="alert alert-error">⚠ <?= htmlspecialchars($error) ?></div>
  <?php endif; ?>

  <!-- Add new code -->
  <div class="card">
    <div class="card-title">Add New Reason Code</div>
    <form method="POST">
      <input type="hidden" name="action" value="add"/>
      <div class="form-grid">
        <div class="form-group">
          <label>Reason Code *</label>
          <input type="text" name="code" placeholder="e.g. 6, 40, D, ERR" required/>
        </div>
        <div class="form-group">
          <label>Medical Aid *</label>
          <select name="medical_aid">
            <?php foreach ($medical_aids as $aid): ?>
            <option value="<?= htmlspecialchars($aid) ?>">
              <?= htmlspecialchars($aid) ?>
            </option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="form-group">
          <label>Classification *</label>
          <select name="classification">
            <?php foreach ($classifications as $cls): ?>
            <option value="<?= htmlspecialchars($cls) ?>"><?= htmlspecialchars($cls) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Description — plain English explanation of this code *</label>
        <input type="text" name="description"
               placeholder="e.g. Amount claimed exceeds tariff amount" required/>
      </div>
      <div class="form-group">
        <label>Action Required — what the practice should do</label>
        <input type="text" name="action_text"
               placeholder="e.g. Assess: write off or bill patient for difference"/>
      </div>
      <button type="submit" class="btn btn-primary">+ Add Code</button>
    </form>
  </div>

  <!-- Existing codes -->
  <div class="card">
    <div class="flex justify-between items-center mb-2">
      <div class="card-title" style="margin:0;border:0">
        Configured Codes (<?= count($codes) ?>)
      </div>
      <div>
        <select id="aid-filter" onchange="filterCodes()"
                style="padding:0.4rem 0.6rem;border:1.5px solid #d1d5db;border-radius:6px;font-size:0.82rem">
          <option value="">Show all aids</option>
          <?php foreach ($medical_aids as $aid): ?>
          <option value="<?= htmlspecialchars($aid) ?>"><?= htmlspecialchars($aid) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
    </div>
    <div class="table-wrap">
      <table id="codes-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Medical Aid</th>
            <th>Description</th>
            <th>Classification</th>
            <th>Action Required</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($codes as $code): ?>
          <tr data-aid="<?= htmlspecialchars($code['medical_aid']) ?>">
            <td><strong><?= htmlspecialchars($code['code']) ?></strong></td>
            <td><?= htmlspecialchars($code['medical_aid']) ?></td>
            <td><?= htmlspecialchars($code['description']) ?></td>
            <td>
              <span class="badge <?= badge_class($code['classification']) ?>">
                <?= htmlspecialchars($code['classification']) ?>
              </span>
            </td>
            <td><?= htmlspecialchars($code['action']) ?></td>
            <td>
              <div class="flex gap-1">
                <button class="btn btn-outline btn-sm"
                        onclick="openEditModal(<?= htmlspecialchars(json_encode($code)) ?>)">
                  Edit
                </button>
                <form method="POST" id="del-<?= htmlspecialchars($code['id']) ?>">
                  <input type="hidden" name="action"  value="delete"/>
                  <input type="hidden" name="code_id" value="<?= htmlspecialchars($code['id']) ?>"/>
                  <button type="button" class="btn btn-danger btn-sm"
                          onclick="confirmDelete('Delete code <?= htmlspecialchars($code['code']) ?>?',
                                   'del-<?= htmlspecialchars($code['id']) ?>')">
                    Delete
                  </button>
                </form>
              </div>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- Edit modal -->
<div class="modal-backdrop" id="edit-modal">
  <div class="modal">
    <div class="modal-title">Edit Reason Code</div>
    <form method="POST" id="edit-form">
      <input type="hidden" name="action"  value="edit"/>
      <input type="hidden" name="code_id" id="edit-id"/>
      <div class="form-grid">
        <div class="form-group">
          <label>Code *</label>
          <input type="text" name="code" id="edit-code" required/>
        </div>
        <div class="form-group">
          <label>Medical Aid *</label>
          <select name="medical_aid" id="edit-aid">
            <?php foreach ($medical_aids as $aid): ?>
            <option value="<?= htmlspecialchars($aid) ?>"><?= htmlspecialchars($aid) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label>Classification *</label>
        <select name="classification" id="edit-cls">
          <?php foreach ($classifications as $cls): ?>
          <option value="<?= htmlspecialchars($cls) ?>"><?= htmlspecialchars($cls) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Description *</label>
        <input type="text" name="description" id="edit-desc" required/>
      </div>
      <div class="form-group">
        <label>Action Required</label>
        <input type="text" name="action_text" id="edit-action"/>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary"
                onclick="closeModal('edit-modal')">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Changes</button>
      </div>
    </form>
  </div>
</div>

<script>
function openEditModal(code) {
  document.getElementById('edit-id').value     = code.id;
  document.getElementById('edit-code').value   = code.code;
  document.getElementById('edit-desc').value   = code.description;
  document.getElementById('edit-action').value = code.action;
  document.getElementById('edit-aid').value    = code.medical_aid;
  document.getElementById('edit-cls').value    = code.classification;
  openModal('edit-modal');
}

function filterCodes() {
  const val  = document.getElementById('aid-filter').value;
  document.querySelectorAll('#codes-table tbody tr').forEach(row => {
    row.style.display = (!val || row.dataset.aid === val) ? '' : 'none';
  });
}
</script>

<?php require __DIR__ . '/includes/footer.php'; ?>