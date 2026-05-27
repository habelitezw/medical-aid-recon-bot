# =============================================================
# db.py  —  MySQL database and local file storage
# Replaces Supabase with MySQL + filesystem
# =============================================================

import os
import uuid
import mysql.connector
from datetime import datetime
from config import (MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE,
                    MYSQL_USER, MYSQL_PASSWORD, RECON_OUTPUT_DIR)

os.makedirs(RECON_OUTPUT_DIR, exist_ok=True)


# ── Connection ────────────────────────────────────────────────

def get_conn():
    """Return a new MySQL connection."""
    return mysql.connector.connect(
        host     = MYSQL_HOST,
        port     = MYSQL_PORT,
        database = MYSQL_DATABASE,
        user     = MYSQL_USER,
        password = MYSQL_PASSWORD,
        charset  = "utf8mb4",
    )


def _fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def _fetchall(cursor):
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


# ── Reason codes ──────────────────────────────────────────────

def db_get_reason_codes():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, code, medical_aid, description, "
            "classification, action, created_by, "
            "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%s') AS created_at "
            "FROM reason_codes ORDER BY medical_aid, code"
        )
        return _fetchall(cur)
    finally:
        conn.close()


def db_add_reason_code(code, medical_aid, description,
                       classification, action, user_id=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        new_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO reason_codes "
            "(id, code, medical_aid, description, classification, action, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (new_id, code.strip().upper(), medical_aid,
             description.strip(), classification.strip(),
             action.strip(), user_id)
        )
        conn.commit()
        return {"id": new_id}
    finally:
        conn.close()


def db_update_reason_code(code_id, code, medical_aid,
                          description, classification, action):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE reason_codes SET code=%s, medical_aid=%s, "
            "description=%s, classification=%s, action=%s "
            "WHERE id=%s",
            (code.strip().upper(), medical_aid, description.strip(),
             classification.strip(), action.strip(), code_id)
        )
        conn.commit()
    finally:
        conn.close()


def db_delete_reason_code(code_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM reason_codes WHERE id=%s", (code_id,))
        conn.commit()
    finally:
        conn.close()


# ── Users ─────────────────────────────────────────────────────

def db_get_user_by_email(email):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email.lower(),))
        return _fetchone(cur)
    finally:
        conn.close()


def db_get_user_by_id(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        return _fetchone(cur)
    finally:
        conn.close()


def db_get_all_users():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, name, role, is_active, "
            "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%s') AS created_at, "
            "DATE_FORMAT(last_login, '%Y-%m-%dT%H:%i:%s') AS last_login "
            "FROM users ORDER BY created_at"
        )
        return _fetchall(cur)
    finally:
        conn.close()


def db_create_user(email, name, password_hash, role="user"):
    conn = get_conn()
    try:
        cur = conn.cursor()
        new_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, email, name, password_hash, role) "
            "VALUES (%s,%s,%s,%s,%s)",
            (new_id, email.lower().strip(), name.strip(),
             password_hash, role)
        )
        conn.commit()
        return db_get_user_by_id(new_id)
    finally:
        conn.close()


def db_update_user(user_id, updates):
    if not updates:
        return
    conn = get_conn()
    try:
        cur = conn.cursor()
        fields = ", ".join(f"{k}=%s" for k in updates)
        values = list(updates.values()) + [user_id]
        cur.execute(f"UPDATE users SET {fields} WHERE id=%s", values)
        conn.commit()
    finally:
        conn.close()


def db_update_last_login(user_id):
    db_update_user(user_id, {"last_login": datetime.now()})


# ── Recon runs ────────────────────────────────────────────────

def db_save_run(user_id, pdf_count, excel_claims, matched_count,
                shortfall_total, error_count, output_filename, output_url):
    """
    output_url is the local file path for MySQL storage.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        new_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO recon_runs "
            "(id, user_id, pdf_count, excel_claims, matched_count, "
            "shortfall_total_usd, error_count, output_filename, output_filepath) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (new_id, user_id, pdf_count, excel_claims, matched_count,
             float(shortfall_total), error_count,
             output_filename, output_url)
        )
        conn.commit()
        cur.execute("SELECT * FROM recon_runs WHERE id=%s", (new_id,))
        return _fetchone(cur)
    finally:
        conn.close()


def db_get_runs(user_id=None, limit=100):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if user_id:
            cur.execute(
                "SELECT r.*, u.name AS user_name, u.email AS user_email "
                "FROM recon_runs r JOIN users u ON r.user_id = u.id "
                "WHERE r.user_id=%s "
                "ORDER BY r.run_date DESC LIMIT %s",
                (user_id, limit)
            )
        else:
            cur.execute(
                "SELECT r.*, u.name AS user_name, u.email AS user_email "
                "FROM recon_runs r JOIN users u ON r.user_id = u.id "
                "ORDER BY r.run_date DESC LIMIT %s",
                (limit,)
            )
        rows = _fetchall(cur)
        # Normalise to match Supabase response shape PHP expects
        for row in rows:
            row["users"] = {
                "name" : row.pop("user_name", ""),
                "email": row.pop("user_email", "")
            }
            # Convert decimals to float for JSON serialisation
            if "shortfall_total_usd" in row:
                row["shortfall_total_usd"] = float(row["shortfall_total_usd"])
        return rows
    finally:
        conn.close()


def db_get_run_by_id(run_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recon_runs WHERE id=%s", (run_id,))
        row = _fetchone(cur)
        if row and "shortfall_total_usd" in row:
            row["shortfall_total_usd"] = float(row["shortfall_total_usd"])
        return row
    finally:
        conn.close()


# ── File storage (local filesystem) ──────────────────────────

def storage_save(file_bytes, filename):
    """Save output file to local filesystem. Returns the file path."""
    path = os.path.join(RECON_OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


def storage_get_path(filename):
    """Return the full path to a stored output file."""
    return os.path.join(RECON_OUTPUT_DIR, filename)