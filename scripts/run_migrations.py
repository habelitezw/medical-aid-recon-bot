#!/usr/bin/env python3
"""Run tracked database migrations for the current release."""

import importlib.util
import re
import sys
from pathlib import Path
from typing import List, Set


MIN_PYTHON = (3, 11)

if sys.version_info < MIN_PYTHON:
    current = ".".join(str(part) for part in sys.version_info[:3])
    required = ".".join(str(part) for part in MIN_PYTHON)
    raise SystemExit(
        f"Python {required}+ is required for migrations; found {current}. "
        "Configure PYTHON_BIN or let the deployment bootstrap detect the Passenger interpreter."
    )


RELEASE_DIR = Path(__file__).resolve().parent.parent
VENDOR_DIR = RELEASE_DIR / "vendor"

if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))
if str(RELEASE_DIR) not in sys.path:
    sys.path.insert(0, str(RELEASE_DIR))

from config import DB_BACKEND  # noqa: E402


def _migration_files(migrations_dir: Path) -> List[Path]:
    pattern = re.compile(r"^\d+_.+\.(sql|py)$")
    return sorted(
        path for path in migrations_dir.iterdir()
        if path.is_file() and pattern.match(path.name)
    )


def _ensure_schema_migrations_table(connection) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) NOT NULL PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        connection.commit()
    finally:
        cursor.close()


def _applied_versions(connection) -> Set[str]:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()


def _apply_sql_migration(connection, migration_path: Path) -> None:
    sql = migration_path.read_text(encoding="utf-8")
    cursor = connection.cursor()
    try:
        statements = [part.strip() for part in sql.split(";") if part.strip()]
        for statement in statements:
            cursor.execute(statement)
            if getattr(cursor, "with_rows", False):
                cursor.fetchall()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _apply_python_migration(connection, migration_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        f"migration_{migration_path.stem}", migration_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration {migration_path.name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        raise RuntimeError(
            f"Python migration {migration_path.name} must define run(connection, release_dir)"
        )

    try:
        module.run(connection, RELEASE_DIR)
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _record_version(connection, version: str) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            (version,),
        )
        connection.commit()
    finally:
        cursor.close()


def run_mysql_migrations() -> int:
    from db_mysql import get_conn  # noqa: E402

    migrations_dir = RELEASE_DIR / "migrations" / "mysql"
    if not migrations_dir.is_dir():
        print(f"No MySQL migrations directory found at {migrations_dir}")
        return 0

    connection = get_conn()
    try:
        _ensure_schema_migrations_table(connection)
        applied_versions = _applied_versions(connection)
        pending_migrations = [
            path for path in _migration_files(migrations_dir)
            if path.name not in applied_versions
        ]

        if not pending_migrations:
            print("No pending MySQL migrations.")
            return 0

        for migration_path in pending_migrations:
            print(f"Applying migration {migration_path.name}")
            if migration_path.suffix == ".sql":
                _apply_sql_migration(connection, migration_path)
            else:
                _apply_python_migration(connection, migration_path)
            _record_version(connection, migration_path.name)

        print(f"Applied {len(pending_migrations)} MySQL migration(s).")
        return 0
    finally:
        connection.close()


def main() -> int:
    if DB_BACKEND == "supabase":
        print("Skipping migrations because DB_BACKEND=supabase.")
        return 0

    if DB_BACKEND != "mysql":
        print(f"Unsupported DB_BACKEND for migrations: {DB_BACKEND}", file=sys.stderr)
        return 1

    return run_mysql_migrations()


if __name__ == "__main__":
    raise SystemExit(main())
