# test_api.py — Full end-to-end API test
# Tests: login, run reconciliation, storage upload, history

import urllib.request
import urllib.error
import json
import os

API = "https://medical-aid-recon-bot.onrender.com"

# ── Files to upload ───────────────────────────────────────────
EXCEL = r"D:\Medical Aid\TestData\Test_Client_Data.xlsx"
PDFS  = [
    r"D:\Medical Aid\TestData\alliance_cimas_test_recon.pdf",
    r"D:\Medical Aid\TestData\alliance_fmh_test_recon.pdf",
    r"D:\Medical Aid\TestData\alliance_ruth_test_recon.pdf",
    r"D:\Medical Aid\TestData\alliance_bonvie_test_recon.pdf",
    r"D:\Medical Aid\TestData\corrupt_test.pdf",
]

def api(endpoint, method="GET", data=None, token=None):
    url     = API + endpoint
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        res = urllib.request.urlopen(req, timeout=30)
        return json.loads(res.read()), res.getcode()
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("=" * 55)
print("Medical Aid Recon Bot — End-to-End API Test")
print("=" * 55)

# Step 1: Login
print("\n[1] Login...")
res, code = api("/api/auth/login", "POST",
                {"email": "takurajunia@gmail.com", "password": "Habelite2026"})
assert code == 200, f"Login failed: {res}"
token = res["token"]
print(f"    ✓ Logged in as {res['user']['name']} ({res['user']['role']})")

# Step 2: Health check
print("\n[2] Health check...")
res, code = api("/api/health")
assert code == 200 and res["status"] == "ok", f"Health check failed: {res}"
print(f"    ✓ API version {res['version']} is healthy")

# Step 3: Get reason codes
print("\n[3] Reason codes...")
res, code = api("/api/codes", token=token)
assert code == 200, f"Codes failed: {res}"
print(f"    ✓ {len(res['codes'])} reason codes loaded from database")

# Step 4: Run reconciliation via multipart upload
print("\n[4] Running reconciliation (this may take 30-60s on cold start)...")

import urllib.parse
import mimetypes

boundary = "----ReconBotBoundary7MA4YWxkTrZu0gW"

def build_multipart(excel_path, pdf_paths):
    body_parts = []

    def add_file(field, path, mime):
        filename = os.path.basename(path)
        with open(path, "rb") as f:
            data = f.read()
        part  = f"--{boundary}\r\n"
        part += f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        part += f"Content-Type: {mime}\r\n\r\n"
        body_parts.append(part.encode() + data + b"\r\n")

    add_file("excel_file", excel_path,
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    for pdf in pdf_paths:
        add_file("pdf_files", pdf, "application/pdf")

    body_parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(body_parts)

body         = build_multipart(EXCEL, PDFS)
content_type = f"multipart/form-data; boundary={boundary}"

req = urllib.request.Request(
    API + "/api/recon/run",
    data    = body,
    headers = {
        "Content-Type"  : content_type,
        "Authorization" : "Bearer " + token,
        "Accept"        : "application/json",
    },
    method  = "POST"
)

try:
    res  = urllib.request.urlopen(req, timeout=180)
    body = json.loads(res.read())
    code = res.getcode()
except urllib.error.HTTPError as e:
    body = json.loads(e.read())
    code = e.code

if code == 200 and body.get("success"):
    print(f"    ✓ Reconciliation complete")
    print(f"      PDFs processed  : {body['pdf_count']}")
    print(f"      Excel claims    : {body['excel_claims']}")
    print(f"      Matched         : {body['matched_count']}")
    print(f"      Shortfall total : USD {body['shortfall_total']}")
    print(f"      Errors          : {body['error_count']}")
    print(f"      Output file     : {body['filename']}")
    print(f"      Download URL    : {body['download_url'][:60]}...")
    run_id = body.get("run_id")
else:
    print(f"    ✗ Reconciliation failed (HTTP {code}): {body}")
    run_id = None

# Step 5: Check history
print("\n[5] History...")
res, code = api("/api/history", token=token)
assert code == 200, f"History failed: {res}"
runs = res.get("runs", [])
print(f"    ✓ {len(runs)} run(s) in history")
if runs:
    latest = runs[0]
    print(f"      Latest: {latest['output_filename']} — "
          f"USD {latest['shortfall_total_usd']} shortfall")

# Step 6: Download the file for latest run
if runs:
    print("\n[6] Download latest run file...")
    latest_id = runs[0]["id"]
    url = f"http://127.0.0.1:5000/api/history/{latest_id}/download"
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token})
    try:
        res  = urllib.request.urlopen(req, timeout=30)
        data = res.read()
        ct   = res.headers.get("Content-Type", "")
        print(f"    ✓ File downloaded successfully")
        print(f"      Size: {len(data):,} bytes")
        print(f"      Content-Type: {ct}")
    except Exception as e:
        print(f"    ✗ Download failed: {e}")