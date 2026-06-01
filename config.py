# =============================================================
# config.py  —  All settings for the Medical Aid Recon Bot
# =============================================================

import os

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()


def _environment_value(name):
    return os.environ.get(name, "").strip()


def _require_production_values(*names):
    if APP_ENV != "production":
        return

    missing = [name for name in names if not _environment_value(name)]
    if missing:
        raise RuntimeError(
            "Missing required production environment variables: "
            + ", ".join(missing)
        )


# ── Local folder paths (used by recon_bot.py CLI only) ───────
INTAKE_FOLDER    = r"D:\Medical Aid\Files"
PROCESSED_FOLDER = r"D:\Medical Aid\Files\Processed"
OUTPUT_FOLDER    = r"D:\Medical Aid\Files\Output"
EXCEL_CLAIMS     = r"D:\Medical Aid\Files\Client Data.xlsx"

# ── JWT ───────────────────────────────────────────────────────
JWT_SECRET = _environment_value("JWT_SECRET")
JWT_ALGORITHM     = "HS256"
JWT_EXPIRY_HOURS  = 8

# ── Local reason codes fallback (used if DB unavailable) ─────
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
REASON_CODES_FILE = os.path.join(BASE_DIR, "reason_codes.json")

# ── Excel column names ────────────────────────────────────────
COL_DATE          = "Date"
COL_PAYER         = "Payer"
COL_MEMBER_NAME   = "Primary Medical Aid Member"
COL_MEMBER_NUMBER = "Medical Aid Number"
COL_CLAIM_REF     = "NH263 Claim reference"
COL_CLAIMED_USD   = "MEDICAL AID Amount claimed USD"
COL_REMITTED_USD  = "Medical Aid Amount remitted USD"
COL_DISCREPANCY   = "Medical Aid Discrepancy USD"
COL_REASON        = "Medical Aid          Reason for discrepancy"
COL_STATUS        = "Claim Status"
COL_PATIENT_ID    = "Patient ID "
COL_PHONE         = "Phone Number"

# ── Medical aid name mapping ──────────────────────────────────
MEDICAL_AID_MAP = {
    "alliance"    : "Alliance Health",
    "bonvie"      : "Bonvie",
    "cellmed"     : "CellMed",
    "cimas"       : "Cimas",
    "flimas"      : "FLIMAS",
    "fmh"         : "First Mutual Health",
    "psmas"       : "PSMAS",
    "corrupt"     : "Unknown",
    "gen health"  : "Generation Health",
    "gen_health"  : "Generation Health",
    "genhealth"   : "Generation Health",
    "generation"  : "Generation Health",
    "maisha"      : "Maisha Health Fund",
}

# ── Fuzzy match threshold ─────────────────────────────────────
FUZZY_THRESHOLD = 80

# ── Fallback when no reason code matches ─────────────────────
REASON_ACTION_DEFAULT = ("Unclassified shortfall", "Manual review required")

# ── MySQL Database ────────────────────────────────────────────
MYSQL_HOST     = os.environ.get("MYSQL_HOST",     "localhost")
MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "habelite_recon")
MYSQL_USER     = os.environ.get("MYSQL_USER",     "recon_user")
MYSQL_PASSWORD = _environment_value("MYSQL_PASSWORD")

DB_BACKEND = os.environ.get("DB_BACKEND", "mysql").strip().lower()

# ── Supabase (used when DB_BACKEND=supabase) ──────────────────
SUPABASE_URL     = os.environ.get("SUPABASE_URL", "https://uudmvdpxhghijijutdyx.supabase.co")
SUPABASE_SERVICE = _environment_value("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET  = "recon-outputs"

# ── File storage (local filesystem) ──────────────────────────
RECON_OUTPUT_DIR = os.environ.get(
    "RECON_OUTPUT_DIR",
    os.path.join(BASE_DIR, "recon_outputs")
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
