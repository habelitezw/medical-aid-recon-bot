# =============================================================
# app.py  —  Flask REST API for Medical Aid Recon Bot
# All responses are JSON. UI is handled by PHP frontend.
# =============================================================

import os
import uuid
import shutil
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify

from config import (MEDICAL_AID_MAP, JWT_SECRET, JWT_ALGORITHM,
                    JWT_EXPIRY_HOURS)
from parsers import parse_remittance, load_excel_claims
from recon_bot import build_output, _match_by_invoice, \
                     _match_by_member_number, _match_by_name_date
from reason_engine import lookup_reason
from db import (db_get_user_by_email, db_get_user_by_id,
                db_update_last_login, db_get_all_users,
                db_create_user, db_update_user,
                db_health_check,
                db_get_reason_codes, db_add_reason_code,
                db_update_reason_code, db_delete_reason_code,
                db_save_run, db_get_runs, db_get_run_by_id,
                storage_save, storage_save_blob, storage_get_blob,
                storage_get_path)

app = Flask(__name__)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── CORS headers (allow PHP frontend to call this API) ────────

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = \
        "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = \
        "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return jsonify({}), 200


# ── JWT helpers ───────────────────────────────────────────────

def _make_token(user):
    payload = {
        "sub"  : str(user["id"]),
        "email": user["email"],
        "role" : user["role"],
        "name" : user["name"],
        "exp"  : datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat"  : datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Unauthorised"}), 401
        try:
            payload = _decode_token(auth.split(" ", 1)[1])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Unauthorised"}), 401
        try:
            payload = _decode_token(auth.split(" ", 1)[1])
            if payload.get("role") != "admin":
                return jsonify({"error": "Admin access required"}), 403
            request.user = payload
        except Exception:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Auth endpoints ────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data  = request.get_json()
    email = (data.get("email") or "").strip().lower()
    pw    = (data.get("password") or "").encode()

    user = db_get_user_by_email(email)
    if not user or not user.get("is_active"):
        return jsonify({"error": "Invalid credentials"}), 401

    stored_hash = user["password_hash"].encode()
    if not bcrypt.checkpw(pw, stored_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    db_update_last_login(user["id"])
    token = _make_token(user)
    return jsonify({
        "token": token,
        "user" : {
            "id"   : str(user["id"]),
            "email": user["email"],
            "name" : user["name"],
            "role" : user["role"],
        }
    })


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    user = db_get_user_by_id(request.user["sub"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id"        : str(user["id"]),
        "email"     : user["email"],
        "name"      : user["name"],
        "role"      : user["role"],
        "is_active" : user["is_active"],
        "created_at": str(user["created_at"]),
        "last_login": str(user["last_login"]),
    })


@app.route("/api/auth/change-password", methods=["POST"])
@require_auth
def change_password():
    data        = request.get_json()
    current_pw  = (data.get("current_password") or "").encode()
    new_pw      = (data.get("new_password") or "").encode()

    if len(new_pw) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    user = db_get_user_by_id(request.user["sub"])
    if not bcrypt.checkpw(current_pw, user["password_hash"].encode()):
        return jsonify({"error": "Current password is incorrect"}), 401

    new_hash = bcrypt.hashpw(new_pw, bcrypt.gensalt()).decode()
    db_update_user(user["id"], {"password_hash": new_hash})
    return jsonify({"message": "Password updated successfully"})


# ── Health check ──────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "2.0"})


@app.route("/api/health/db", methods=["GET"])
def db_health():
    try:
        db_health_check()
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        app.logger.exception("Database health check failed")
        return jsonify({"status": "error", "database": "unavailable"}), 503


# ── Reconciliation endpoint ───────────────────────────────────

def _identify_medical_aid(filename):
    name = filename.lower()
    for key, label in MEDICAL_AID_MAP.items():
        if key in name:
            return label
    return "Unknown"


def _run_recon(session_dir, excel_path, pdf_paths):
    import parsers
    original = parsers.EXCEL_CLAIMS
    parsers.EXCEL_CLAIMS = excel_path
    try:
        excel_claims     = load_excel_claims()
        all_transactions = []
        error_log        = []
        match_log        = []

        for pdf_path in pdf_paths:
            filename    = os.path.basename(pdf_path)
            medical_aid = _identify_medical_aid(filename)
            try:
                txs = parse_remittance(pdf_path, medical_aid)
                all_transactions.extend(txs)
            except Exception as e:
                error_log.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    filename, str(e)])

        for tx in all_transactions:
            claim, method = _match_by_invoice(tx, excel_claims)
            if claim is None:
                claim, method = _match_by_member_number(tx, excel_claims)
            if claim is None:
                claim, method = _match_by_name_date(tx, excel_claims)
            if claim is not None:
                tx["matched"]      = True
                tx["match_method"] = method
                tx["phone"]        = claim.get("phone", "")
                claim["matched"]   = True
                match_log.append({"match_method": method,
                                  "invoice": tx.get("invoice_num", ""),
                                  "patient": tx.get("patient_name", "")})
            else:
                tx["matched"]      = False
                tx["match_method"] = "unmatched"

        run_date     = datetime.now()
        wb           = build_output(run_date, all_transactions,
                                    excel_claims, match_log, error_log)
        out_name     = f"RECON_{run_date.strftime('%Y%m%d_%H%M%S')}_ALL.xlsx"
        out_path     = os.path.join(session_dir, out_name)
        wb.save(out_path)

        shortfall_total = round(sum(
            t["shortfall_amt"] for t in all_transactions), 2)

        return {
            "path"           : out_path,
            "filename"       : out_name,
            "pdf_count"      : len(pdf_paths),
            "excel_claims"   : len(excel_claims),
            "matched_count"  : len(match_log),
            "shortfall_total": shortfall_total,
            "error_count"    : len(error_log),
        }
    finally:
        parsers.EXCEL_CLAIMS = original


def _cleanup_old_sessions():
    import time
    cutoff = time.time() - 3600
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if os.path.isdir(path):
            try:
                if os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path)
            except Exception:
                pass


@app.route("/api/recon/run", methods=["POST"])
@require_auth
def run_recon():
    excel_file = request.files.get("excel_file")
    pdf_files  = request.files.getlist("pdf_files")

    if not excel_file or excel_file.filename == "":
        return jsonify({"error": "Excel file required"}), 400
    if not pdf_files or all(f.filename == "" for f in pdf_files):
        return jsonify({"error": "At least one PDF required"}), 400

    session_id  = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        excel_path = os.path.join(session_dir, "Client_Data.xlsx")
        excel_file.save(excel_path)

        pdf_paths = []
        for pdf in pdf_files:
            if pdf.filename == "":
                continue
            safe_name = pdf.filename.replace(" ", "_")
            pdf_path  = os.path.join(session_dir, safe_name)
            pdf.save(pdf_path)
            pdf_paths.append(pdf_path)

        result = _run_recon(session_dir, excel_path, pdf_paths)

        # Read output file bytes
        with open(result["path"], "rb") as f:
            file_bytes = f.read()

        # Save to local filesystem (best effort)
        storage_save(file_bytes, result["filename"])

        # Save run record to database
        run_record = db_save_run(
            user_id         = request.user["sub"],
            pdf_count       = result["pdf_count"],
            excel_claims    = result["excel_claims"],
            matched_count   = result["matched_count"],
            shortfall_total = result["shortfall_total"],
            error_count     = result["error_count"],
            output_filename = result["filename"],
            output_url      = result["filename"],
        )

        # Store file as BLOB in MySQL
        if run_record:
            storage_save_blob(run_record["id"], file_bytes)

        _cleanup_old_sessions()

        return jsonify({
            "success"        : True,
            "run_id"         : str(run_record["id"]) if run_record else None,
            "filename"       : result["filename"],
            "download_url"   : result["filename"],
            "pdf_count"      : result["pdf_count"],
            "excel_claims"   : result["excel_claims"],
            "matched_count"  : result["matched_count"],
            "shortfall_total": result["shortfall_total"],
            "error_count"    : result["error_count"],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            shutil.rmtree(session_dir)
        except Exception:
            pass


# ── History endpoint ──────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
@require_auth
def history():
    role    = request.user.get("role")
    user_id = request.user["sub"] if role != "admin" else None
    runs    = db_get_runs(user_id=user_id, limit=100)
    return jsonify({"runs": runs})


@app.route("/api/history/<run_id>/download", methods=["GET"])
@require_auth
def history_download(run_id):
    """Stream output file — tries BLOB first, then local filesystem."""
    from flask import send_file, Response
    import io

    run = db_get_run_by_id(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    if request.user.get("role") != "admin" and \
            str(run["user_id"]) != request.user["sub"]:
        return jsonify({"error": "Access denied"}), 403

    # Try BLOB storage first
    blob_data, filename = storage_get_blob(run_id)
    if blob_data:
        return send_file(
            io.BytesIO(blob_data),
            as_attachment=True,
            download_name=filename or run["output_filename"],
            mimetype="application/vnd.openxmlformats-officedocument"
                     ".spreadsheetml.sheet"
        )

    # Fall back to storage_get_path — returns URL (Supabase) or local path (MySQL)
    path_or_url = storage_get_path(run["output_filename"])
    if path_or_url:
        # If it's a URL (Supabase signed URL), redirect to it
        if path_or_url.startswith("http"):
            from flask import redirect
            return redirect(path_or_url)
        # Otherwise it's a local file path
        return send_file(
            path_or_url,
            as_attachment=True,
            download_name=run["output_filename"],
            mimetype="application/vnd.openxmlformats-officedocument"
                     ".spreadsheetml.sheet"
        )

    return jsonify({"error": "File not available"}), 404

# ── Reason codes endpoints ────────────────────────────────────

@app.route("/api/codes", methods=["GET"])
@require_auth
def get_codes():
    return jsonify({"codes": db_get_reason_codes()})


@app.route("/api/codes", methods=["POST"])
@require_admin
def add_code():
    d = request.get_json()
    db_add_reason_code(
        d.get("code", ""),
        d.get("medical_aid", "ALL"),
        d.get("description", ""),
        d.get("classification", ""),
        d.get("action", ""),
        request.user["sub"],
    )
    return jsonify({"message": "Code added"}), 201


@app.route("/api/codes/<code_id>", methods=["PUT"])
@require_admin
def update_code(code_id):
    d = request.get_json()
    db_update_reason_code(
        code_id,
        d.get("code", ""),
        d.get("medical_aid", "ALL"),
        d.get("description", ""),
        d.get("classification", ""),
        d.get("action", ""),
    )
    return jsonify({"message": "Code updated"})


@app.route("/api/codes/<code_id>", methods=["DELETE"])
@require_admin
def delete_code(code_id):
    db_delete_reason_code(code_id)
    return jsonify({"message": "Code deleted"})


# ── User management endpoints (admin only) ────────────────────

@app.route("/api/users", methods=["GET"])
@require_admin
def get_users():
    return jsonify({"users": db_get_all_users()})


@app.route("/api/users", methods=["POST"])
@require_admin
def create_user():
    d        = request.get_json()
    email    = (d.get("email") or "").strip().lower()
    name     = (d.get("name") or "").strip()
    password = (d.get("password") or "").encode()
    role     = d.get("role", "user")

    if not email or not name or not password:
        return jsonify({"error": "Email, name and password required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if role not in ("admin", "user"):
        return jsonify({"error": "Role must be admin or user"}), 400

    if db_get_user_by_email(email):
        return jsonify({"error": "Email already exists"}), 409

    pw_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
    user    = db_create_user(email, name, pw_hash, role)
    return jsonify({"message": "User created", "user": user}), 201


@app.route("/api/users/<user_id>", methods=["PUT"])
@require_admin
def update_user(user_id):
    d       = request.get_json()
    updates = {}
    if "name" in d:
        updates["name"] = d["name"].strip()
    if "role" in d and d["role"] in ("admin", "user"):
        updates["role"] = d["role"]
    if "is_active" in d:
        updates["is_active"] = bool(d["is_active"])
    if "password" in d and d["password"]:
        if len(d["password"]) < 8:
            return jsonify({"error": "Password too short"}), 400
        updates["password_hash"] = bcrypt.hashpw(
            d["password"].encode(), bcrypt.gensalt()).decode()
    if updates:
        db_update_user(user_id, updates)
    return jsonify({"message": "User updated"})


@app.route("/api/users/<user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    if user_id == request.user["sub"]:
        return jsonify({"error": "Cannot delete your own account"}), 400
    db_update_user(user_id, {"is_active": False})
    return jsonify({"message": "User deactivated"})


if __name__ == "__main__":
    app.run(debug=False, host=os.environ.get("HOST", "127.0.0.1"), port=5000)
