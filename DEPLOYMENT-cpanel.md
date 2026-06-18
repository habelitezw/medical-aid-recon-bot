# cPanel Deployment

This project runs as two apps on the same cPanel account:

- `recon-portal/` is the PHP frontend.
- `app.py` is the Flask API loaded by cPanel Python App / Passenger.

## Recommended layout

Deploy the repository to a directory such as:

- `~/medical-aid-recon-bot/`

Then configure cPanel like this:

- Python app root: `~/medical-aid-recon-bot`
- Python startup file: `passenger_wsgi.py`
- Python application URL: `/recon-api`
- PHP document root: `~/medical-aid-recon-bot/recon-portal`

With that layout, the Flask route:

- `/api/auth/login`

is exposed publicly as:

- `https://your-domain.example/recon-api/api/auth/login`

and the PHP portal should use:

- `API_BASE_URL=https://your-domain.example/recon-api`

## First-time cPanel setup

1. Create a MySQL database and user in cPanel.
2. Upload this repository to your chosen project directory.
3. In cPanel, create a Python application pointing at the project root.
4. Install Python packages into that app's virtualenv:

```bash
pip install -r requirements.txt
```

5. Restart the Python application in cPanel.
6. Point your domain or subdomain document root to `recon-portal/`.

## Runtime config files

The app reads two deploy-time config files:

- `.env` for Python settings
- `recon-portal/config.local.php` for PHP settings

The GitHub Action generates both files from secrets before uploading.
The PHP deployment bootstrap will try to detect the running Passenger Python interpreter automatically. If you know the exact interpreter path, you can still provide it as `CPANEL_PYTHON_BIN` and it will be written into the release `.env` as `PYTHON_BIN`.

## Required GitHub Secrets

- `FTP_SERVER`
- `FTP_USERNAME`
- `FTP_PASSWORD`
- `FTP_PORT`
- `FTP_TARGET_DIR`
- `API_BASE_URL`
- `JWT_SECRET`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`

## Optional GitHub Secrets

- `APP_NAME`
- `APP_VERSION`
- `SESSION_NAME`
- `SESSION_LIFETIME`
- `RECON_OUTPUT_DIR`
- `RECON_UPLOAD_DIR`
- `CPANEL_PYTHON_BIN` - optional override for the absolute path to the cPanel Python app interpreter

## Local development fallback

If no deploy-time config is present:

- PHP defaults to `http://127.0.0.1:5000` when running on localhost.
- PHP defaults to `https://<host>/recon-api` on non-local hosts.
- Python loads `.env` automatically when present.
