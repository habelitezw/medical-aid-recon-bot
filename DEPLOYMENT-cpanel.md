# cPanel Deployment

This project now deploys directly into the cPanel Python app root.
The workflow no longer builds immutable releases, uploads vendored Python packages, or activates releases through a PHP bootstrap endpoint.

## cPanel app settings

Use these values in cPanel:

- Python app root: `~/myclients/medical-aid-recon-bot`
- Python startup file: `passenger_wsgi.py`
- Python entry point: `application`
- Python app URL: `https://habe.co.zw/myclients/medical-aid-recon-bot`

The PHP portal stays inside the same root at:

- `~/myclients/medical-aid-recon-bot/recon-portal`

## GitHub secrets

Required:

- `FTP_SERVER`
- `FTP_USERNAME`
- `FTP_PASSWORD`
- `FTP_SERVER_DIR`
- `API_BASE_URL`
- `JWT_SECRET`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `CPANEL_PYTHON_BIN`

Optional:

- `FTP_PORT`
- `APP_NAME`
- `APP_VERSION`
- `SESSION_NAME`
- `SESSION_LIFETIME`
- `RECON_OUTPUT_DIR`
- `RECON_UPLOAD_DIR`

Use these exact values for the current account:

- `FTP_SERVER_DIR=/myclients/medical-aid-recon-bot/`
- `API_BASE_URL=https://habe.co.zw/myclients/medical-aid-recon-bot`
- `CPANEL_PYTHON_BIN=/home/andyb3l/virtualenv/myclients/medical-aid-recon-bot/3.11/bin/python`

## What the workflow does

1. Validates the Python and PHP code.
2. Copies the repository into a temporary deploy directory.
3. Writes a production `.env` file into the app root.
4. Writes `recon-portal/config.local.php` for the PHP portal.
5. Uploads the app root directly to `FTP_SERVER_DIR`.
6. Uploads `tmp/restart.txt` to trigger a Passenger restart.

## First deploy

1. Create the cPanel Python app with the settings above.
2. Run the GitHub deploy workflow.
3. In cPanel, run `Pip Install` once for `requirements.txt`.
4. Restart the Python app.
5. Test `https://habe.co.zw/myclients/medical-aid-recon-bot/api/health`.

## Ongoing deploys

- Normal code-only deploys only need the GitHub workflow.
- If `requirements.txt` changes, run `Pip Install` in cPanel after the workflow finishes.
- If database migrations change, run `scripts/run_migrations.py` from the cPanel virtualenv or the cPanel Python script runner.

## Notes

- `passenger_wsgi.py` now loads the app directly from the cPanel app root.
- The old release bootstrap files under `deploy/bootstrap/` are no longer part of the active deploy path.
