# =============================================================
# db.py  —  Supabase database and storage client
# =============================================================

import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE, SUPABASE_BUCKET

def get_client() -> Client:
    """Return a Supabase client using the service role key."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE)


# ── Reason codes ──────────────────────────────────────────────

def db_get_reason_codes():
    sb = get_client()
    res = sb.table("reason_codes").select("*").order("medical_aid").order("code").execute()
    return res.data or []

def db_add_reason_code(code, medical_aid, description, classification, action, user_id=None):
    sb = get_client()
    res = sb.table("reason_codes").insert({
        "code"          : code.strip().upper(),
        "medical_aid"   : medical_aid,
        "description"   : description.strip(),
        "classification": classification.strip(),
        "action"        : action.strip(),
        "created_by"    : user_id,
    }).execute()
    return res.data

def db_update_reason_code(code_id, code, medical_aid, description, classification, action):
    sb = get_client()
    res = sb.table("reason_codes").update({
        "code"          : code.strip().upper(),
        "medical_aid"   : medical_aid,
        "description"   : description.strip(),
        "classification": classification.strip(),
        "action"        : action.strip(),
    }).eq("id", code_id).execute()
    return res.data

def db_delete_reason_code(code_id):
    sb = get_client()
    sb.table("reason_codes").delete().eq("id", code_id).execute()


# ── Users ─────────────────────────────────────────────────────

def db_get_user_by_email(email):
    sb = get_client()
    res = sb.table("users").select("*").eq("email", email.lower()).execute()
    return res.data[0] if res.data else None

def db_get_user_by_id(user_id):
    sb = get_client()
    res = sb.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def db_get_all_users():
    sb = get_client()
    res = sb.table("users").select(
        "id, email, name, role, is_active, created_at, last_login"
    ).order("created_at").execute()
    return res.data or []

def db_create_user(email, name, password_hash, role="user"):
    sb = get_client()
    res = sb.table("users").insert({
        "email"        : email.lower().strip(),
        "name"         : name.strip(),
        "password_hash": password_hash,
        "role"         : role,
    }).execute()
    return res.data[0] if res.data else None

def db_update_user(user_id, updates):
    sb = get_client()
    res = sb.table("users").update(updates).eq("id", user_id).execute()
    return res.data

def db_update_last_login(user_id):
    sb = get_client()
    sb.table("users").update({"last_login": "now()"}).eq("id", user_id).execute()


# ── Recon runs ────────────────────────────────────────────────

def db_save_run(user_id, pdf_count, excel_claims, matched_count,
                shortfall_total, error_count, output_filename, output_url):
    sb = get_client()
    res = sb.table("recon_runs").insert({
        "user_id"            : user_id,
        "pdf_count"          : pdf_count,
        "excel_claims"       : excel_claims,
        "matched_count"      : matched_count,
        "shortfall_total_usd": float(shortfall_total),
        "error_count"        : error_count,
        "output_filename"    : output_filename,
        "output_url"         : output_url,
    }).execute()
    return res.data[0] if res.data else None

def db_get_runs(user_id=None, limit=50):
    sb = get_client()
    query = sb.table("recon_runs").select(
        "*, users(name, email)"
    ).order("run_date", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    res = query.execute()
    return res.data or []


# ── File storage ──────────────────────────────────────────────

def storage_upload(file_bytes, filename):
    """Upload file to Supabase storage. Returns public URL."""
    sb = get_client()
    path = f"runs/{filename}"
    sb.storage.from_(SUPABASE_BUCKET).upload(
        path, file_bytes,
        file_options={"content-type":
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    )
    # Generate a signed URL valid for 7 days
    res = sb.storage.from_(SUPABASE_BUCKET).create_signed_url(path, 604800)
    return res.get("signedURL") or res.get("signed_url") or ""

def storage_get_signed_url(filename, expires_in=604800):
    """Get a fresh signed URL for an existing file."""
    sb = get_client()
    path = f"runs/{filename}"
    res = sb.storage.from_(SUPABASE_BUCKET).create_signed_url(path, expires_in)
    return res.get("signedURL") or res.get("signed_url") or ""