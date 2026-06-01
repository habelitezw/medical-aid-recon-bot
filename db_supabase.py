# =============================================================
# db_supabase.py  —  Supabase database implementation
# Used when DB_BACKEND=supabase (Render deployment)
# =============================================================

import os
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE, SUPABASE_BUCKET, RECON_OUTPUT_DIR

os.makedirs(RECON_OUTPUT_DIR, exist_ok=True)


def _sb():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE)


def db_health_check():
    _sb().table("reason_codes").select("id").limit(1).execute()


# ── Reason codes ──────────────────────────────────────────────

def db_get_reason_codes():
    res = _sb().table("reason_codes").select("*").order("medical_aid").order("code").execute()
    return res.data or []


def db_add_reason_code(code, medical_aid, description,
                       classification, action, user_id=None):
    res = _sb().table("reason_codes").insert({
        "code": code.strip().upper(), "medical_aid": medical_aid,
        "description": description.strip(),
        "classification": classification.strip(),
        "action": action.strip(), "created_by": user_id,
    }).execute()
    return res.data


def db_update_reason_code(code_id, code, medical_aid,
                          description, classification, action):
    _sb().table("reason_codes").update({
        "code": code.strip().upper(), "medical_aid": medical_aid,
        "description": description.strip(),
        "classification": classification.strip(),
        "action": action.strip(),
    }).eq("id", code_id).execute()


def db_delete_reason_code(code_id):
    _sb().table("reason_codes").delete().eq("id", code_id).execute()


# ── Users ─────────────────────────────────────────────────────

def db_get_user_by_email(email):
    res = _sb().table("users").select("*").eq("email", email.lower()).execute()
    return res.data[0] if res.data else None


def db_get_user_by_id(user_id):
    res = _sb().table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None


def db_get_all_users():
    res = _sb().table("users").select(
        "id, email, name, role, is_active, created_at, last_login"
    ).order("created_at").execute()
    return res.data or []


def db_create_user(email, name, password_hash, role="user"):
    res = _sb().table("users").insert({
        "email": email.lower().strip(), "name": name.strip(),
        "password_hash": password_hash, "role": role,
    }).execute()
    return res.data[0] if res.data else None


def db_update_user(user_id, updates):
    _sb().table("users").update(updates).eq("id", user_id).execute()


def db_update_last_login(user_id):
    _sb().table("users").update({"last_login": "now()"}).eq("id", user_id).execute()


# ── Recon runs ────────────────────────────────────────────────

def db_save_run(user_id, pdf_count, excel_claims, matched_count,
                shortfall_total, error_count, output_filename, output_url):
    res = _sb().table("recon_runs").insert({
        "user_id": user_id, "pdf_count": pdf_count,
        "excel_claims": excel_claims, "matched_count": matched_count,
        "shortfall_total_usd": float(shortfall_total),
        "error_count": error_count,
        "output_filename": output_filename,
        "output_url": output_url,
    }).execute()
    return res.data[0] if res.data else None


def db_get_runs(user_id=None, limit=100):
    query = _sb().table("recon_runs").select(
        "*, users(name, email)"
    ).order("run_date", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    res = query.execute()
    rows = res.data or []
    for row in rows:
        if "shortfall_total_usd" in row:
            row["shortfall_total_usd"] = float(row["shortfall_total_usd"])
    return rows


def db_get_run_by_id(run_id):
    res = _sb().table("recon_runs").select("*").eq("id", run_id).execute()
    if not res.data:
        return None
    row = res.data[0]
    if "shortfall_total_usd" in row:
        row["shortfall_total_usd"] = float(row["shortfall_total_usd"])
    return row


# ── File storage (Supabase Storage) ──────────────────────────

def storage_save(file_bytes, filename):
    """Save to Supabase Storage. Returns filename as reference."""
    try:
        path = f"runs/{filename}"
        _sb().storage.from_(SUPABASE_BUCKET).upload(
            path, file_bytes,
            file_options={"content-type":
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"}
        )
    except Exception:
        pass
    return filename


def storage_save_blob(run_id, file_bytes):
    """For Supabase backend — update the output_url with signed URL."""
    try:
        run = db_get_run_by_id(run_id)
        if run:
            filename = run.get("output_filename", "")
            path = f"runs/{filename}"
            res  = _sb().storage.from_(SUPABASE_BUCKET).create_signed_url(
                path, 604800)
            signed_url = res.get("signedURL") or res.get("signed_url") or ""
            if signed_url:
                _sb().table("recon_runs").update(
                    {"output_url": signed_url}
                ).eq("id", run_id).execute()
    except Exception:
        pass


def storage_get_blob(run_id):
    """For Supabase — return None (use signed URL instead)."""
    return None, None


def storage_get_path(filename):
    """For Supabase — return signed URL."""
    try:
        path = f"runs/{filename}"
        res  = _sb().storage.from_(SUPABASE_BUCKET).create_signed_url(
            path, 604800)
        return res.get("signedURL") or res.get("signed_url")
    except Exception:
        return None
