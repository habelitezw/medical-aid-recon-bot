# =============================================================
# db.py  —  Database router
# Routes all calls to either db_mysql.py or db_supabase.py
# based on the DB_BACKEND environment variable.
# =============================================================

from config import DB_BACKEND

if DB_BACKEND == "supabase":
    from db_supabase import *
    from db_supabase import (
        db_get_reason_codes, db_add_reason_code,
        db_update_reason_code, db_delete_reason_code,
        db_health_check,
        db_get_user_by_email, db_get_user_by_id,
        db_get_all_users, db_create_user,
        db_update_user, db_update_last_login,
        db_save_run, db_get_runs, db_get_run_by_id,
        storage_save, storage_save_blob,
        storage_get_blob, storage_get_path,
    )
else:
    from db_mysql import *
    from db_mysql import (
        db_get_reason_codes, db_add_reason_code,
        db_update_reason_code, db_delete_reason_code,
        db_health_check,
        db_get_user_by_email, db_get_user_by_id,
        db_get_all_users, db_create_user,
        db_update_user, db_update_last_login,
        db_save_run, db_get_runs, db_get_run_by_id,
        storage_save, storage_save_blob,
        storage_get_blob, storage_get_path,
    )
