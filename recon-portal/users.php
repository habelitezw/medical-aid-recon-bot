<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_admin();

$page_title = 'User Management';
$message    = '';
$error      = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'create') {
        $res = api_call('/api/users', 'POST', [
            'email'    => $_POST['email']    ?? '',
            'name'     => $_POST['name']     ?? '',
            'password' => $_POST['password'] ?? '',
            'role'     => $_POST['role']     ?? 'user',
        ]);
        $message = isset($res['message']) ? 'User created successfully.' : '';
        $error   = $res['error'] ?? '';

    } elseif ($action === 'edit') {
        $updates = [
            'name' => $_POST['name'] ?? '',
            'role' => $_POST['role'] ?? 'user',
        ];
        if (!empty($_POST['password'])) {
            $updates['password'] = $_POST['password'];
        }
        $res     = api_call('/api/users/' . ($_POST['user_id'] ?? ''), 'PUT', $updates);
        $message = $res['message'] ?? '';
        $error   = $res['error']   ?? '';

    } elseif ($action === 'toggle') {
        $is_active = ($_POST['is_active'] ?? '1') === '1';
        $res       = api_call('/api/users/' . ($_POST['user_id'] ?? ''), 'PUT',
                              ['is_active' => !$is_active]);
        $message   = $res['message'] ?? '';
        $error     = $res['error']   ?? '';
    }
}

$users_res = api_call('/api/users');
$users     = $users_res['users'] ?? [];
?>
<?php require __DIR__ . '/includes/header.php'; ?>
<?php require __DIR__ . '/includes/sidebar.php'; ?>

<div class="main-content">
  <div class="page-header">
    <div class="flex justify-between items-center">
      <div>
        <h1>👤 User Management</h1>
        <p>Manage who can access the reconciliation portal.</p>
      </div>
      <button class="btn btn-primary" onclick="openModal('create-modal')">
        + Add User
      </button>
    </div>
  </div>

  <?php if ($message): ?>
  <div class="alert alert-success" data-auto-dismiss>✓ <?= htmlspecialchars($message) ?></div>
  <?php endif; ?>
  <?php if ($error): ?>
  <div class="alert alert-error">⚠ <?= htmlspecialchars($error) ?></div>
  <?php endif; ?>

  <div class="card">
    <div class="card-title"><?= count($users) ?> user<?= count($users) !== 1 ? 's' : '' ?></div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Last Login</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($users as $u): ?>
          <tr>
            <td><?= htmlspecialchars($u['name']) ?></td>
            <td><?= htmlspecialchars($u['email']) ?></td>
            <td>
              <span class="badge badge-<?= $u['role'] ?>">
                <?= htmlspecialchars($u['role']) ?>
              </span>
            </td>
            <td>
              <span class="badge badge-<?= $u['is_active'] ? 'active' : 'inactive' ?>">
                <?= $u['is_active'] ? 'Active' : 'Inactive' ?>
              </span>
            </td>
            <td class="text-muted" style="font-size:0.78rem">
              <?= $u['last_login'] ? date('d M Y H:i', strtotime($u['last_login'])) : 'Never' ?>
            </td>
            <td class="text-muted" style="font-size:0.78rem">
              <?= date('d M Y', strtotime($u['created_at'])) ?>
            </td>
            <td>
              <div class="flex gap-1">
                <button class="btn btn-outline btn-sm"
                        onclick="openEditModal(<?= htmlspecialchars(json_encode($u)) ?>)">
                  Edit
                </button>
                <?php if ($u['id'] !== get_user()['id']): ?>
                <form method="POST">
                  <input type="hidden" name="action"    value="toggle"/>
                  <input type="hidden" name="user_id"   value="<?= $u['id'] ?>"/>
                  <input type="hidden" name="is_active" value="<?= $u['is_active'] ? '1' : '0' ?>"/>
                  <button type="submit" class="btn btn-sm
                          <?= $u['is_active'] ? 'btn-danger' : 'btn-success' ?>">
                    <?= $u['is_active'] ? 'Deactivate' : 'Activate' ?>
                  </button>
                </form>
                <?php endif; ?>
              </div>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- Create user modal -->
<div class="modal-backdrop" id="create-modal">
  <div class="modal">
    <div class="modal-title">Add New User</div>
    <form method="POST">
      <input type="hidden" name="action" value="create"/>
      <div class="form-group">
        <label>Full Name *</label>
        <input type="text" name="name" required/>
      </div>
      <div class="form-group">
        <label>Email Address *</label>
        <input type="email" name="email" required/>
      </div>
      <div class="form-group">
        <label>Password * (minimum 8 characters)</label>
        <input type="password" name="password" required minlength="8"/>
      </div>
      <div class="form-group">
        <label>Role *</label>
        <select name="role">
          <option value="user">User — can run reconciliations and view history</option>
          <option value="admin">Admin — full access including user and code management</option>
        </select>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary"
                onclick="closeModal('create-modal')">Cancel</button>
        <button type="submit" class="btn btn-primary">Create User</button>
      </div>
    </form>
  </div>
</div>

<!-- Edit user modal -->
<div class="modal-backdrop" id="edit-modal">
  <div class="modal">
    <div class="modal-title">Edit User</div>
    <form method="POST">
      <input type="hidden" name="action"  value="edit"/>
      <input type="hidden" name="user_id" id="edit-id"/>
      <div class="form-group">
        <label>Full Name *</label>
        <input type="text" name="name" id="edit-name" required/>
      </div>
      <div class="form-group">
        <label>Role *</label>
        <select name="role" id="edit-role">
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <div class="form-group">
        <label>New Password (leave blank to keep current)</label>
        <input type="password" name="password" minlength="8"/>
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
function openEditModal(u) {
  document.getElementById('edit-id').value   = u.id;
  document.getElementById('edit-name').value = u.name;
  document.getElementById('edit-role').value = u.role;
  openModal('edit-modal');
}
</script>

<?php require __DIR__ . '/includes/footer.php'; ?>