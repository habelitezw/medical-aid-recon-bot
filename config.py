# =============================================================
# config.py  —  All settings for the Medical Aid Recon Bot
# =============================================================

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()


def _environment_value(name: str) -> str:
    return os.environ.get(name, "").strip()


def _require_production_values(*names: str) -> None:
    if APP_ENV != "production":
        return

    missing = [name for name in names if not _environment_value(name)]
    if missing:
        raise RuntimeError(
            "Missing required production environment variables: "
            + ", ".join(missing)
        )


# ── Local folder paths (used by recon_bot.py CLI only) ───────
INTAKE_FOLDER = os.environ.get("INTAKE_FOLDER", r"D:\Medical Aid\Files")
PROCESSED_FOLDER = os.environ.get("PROCESSED_FOLDER", r"D:\Medical Aid\Files\Processed")
OUTPUT_FOLDER = os.environ.get("OUTPUT_FOLDER", r"D:\Medical Aid\Files\Output")
EXCEL_CLAIMS = os.environ.get("EXCEL_CLAIMS", r"D:\Medical Aid\Files\Client Data.xlsx")

# ── JWT ───────────────────────────────────────────────────────
JWT_SECRET = _environment_value("JWT_SECRET") or (
    "habelite-jwt-secret-2026-production-key" if APP_ENV != "production" else ""
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "8"))

# ── Local reason codes fallback (used if DB unavailable) ─────
REASON_CODES_FILE = os.environ.get(
    "REASON_CODES_FILE",
    str(BASE_DIR / "reason_codes.json"),
)

# ── Excel column names ────────────────────────────────────────
COL_DATE = "Date"
COL_PAYER = "Payer"
COL_MEMBER_NAME = "Primary Medical Aid Member"
COL_MEMBER_NUMBER = "Medical Aid Number"
COL_CLAIM_REF = "NH263 Claim reference"
COL_CLAIMED_USD = "MEDICAL AID Amount claimed USD"
COL_REMITTED_USD = "Medical Aid Amount remitted USD"
COL_DISCREPANCY = "Medical Aid Discrepancy USD"
COL_REASON = "Medical Aid          Reason for discrepancy"
COL_STATUS = "Claim Status"
COL_PATIENT_ID = "Patient ID "
COL_PHONE = "Phone Number"

# ── Medical aid name mapping ──────────────────────────────────
MEDICAL_AID_MAP = {
    "alliance": "Alliance Health",
    "bonvie": "Bonvie",
    "cellmed": "CellMed",
    "cimas": "Cimas",
    "flimas": "FLIMAS",
    "fmh": "First Mutual Health",
    "psmas": "PSMAS",
    "corrupt": "Unknown",
    "gen health": "Generation Health",
    "gen_health": "Generation Health",
    "genhealth": "Generation Health",
    "generation": "Generation Health",
    "maisha": "Maisha Health Fund",
}

# ── Fuzzy match threshold ─────────────────────────────────────
FUZZY_THRESHOLD = 80

# ── Fallback when no reason code matches ─────────────────────
REASON_ACTION_DEFAULT = ("Unclassified shortfall", "Manual review required")

# ── MySQL Database ────────────────────────────────────────────
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "medical_aid_recon")
MYSQL_USER = os.environ.get("MYSQL_USER", "recon_user")
MYSQL_PASSWORD = _environment_value("MYSQL_PASSWORD")

DB_BACKEND = os.environ.get("DB_BACKEND", "mysql").strip().lower()

# ── Supabase (used when DB_BACKEND=supabase) ──────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://uudmvdpxhghijijutdyx.supabase.co")
SUPABASE_SERVICE = _environment_value("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "recon-outputs")

# ── File storage (local filesystem) ──────────────────────────
RECON_OUTPUT_DIR = os.environ.get(
    "RECON_OUTPUT_DIR",
    str(BASE_DIR / "recon_outputs"),
)

if DB_BACKEND not in ("mysql", "supabase"):
    raise RuntimeError("DB_BACKEND must be either mysql or supabase")

_require_production_values("JWT_SECRET")
if DB_BACKEND == "mysql":
    _require_production_values(
        "MYSQL_HOST",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
    )
else:
    _require_production_values("SUPABASE_URL", "SUPABASE_SERVICE_KEY")
