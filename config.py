# =============================================================
# config.py  —  All settings for the Medical Aid Recon Bot
# =============================================================

import os

# ── Local folder paths (used by recon_bot.py CLI only) ───────
INTAKE_FOLDER    = r"D:\Medical Aid\Files"
PROCESSED_FOLDER = r"D:\Medical Aid\Files\Processed"
OUTPUT_FOLDER    = r"D:\Medical Aid\Files\Output"
EXCEL_CLAIMS     = r"D:\Medical Aid\Files\Client Data.xlsx"

# ── Supabase ──────────────────────────────────────────────────
SUPABASE_URL      = os.environ.get("SUPABASE_URL", "https://uudmvdpxhghijijutdyx.supabase.co")
SUPABASE_ANON     = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE  = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET   = "recon-outputs"

# ── JWT ───────────────────────────────────────────────────────
JWT_SECRET        = os.environ.get("JWT_SECRET", "habelite-jwt-secret-2026")
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
    "alliance" : "Alliance Health",
    "bonvie"   : "Bonvie",
    "cellmed"  : "CellMed",
    "cimas"    : "Cimas",
    "flimas"   : "FLIMAS",
    "fmh"      : "First Mutual Health",
    "psmas"    : "PSMAS",
    "corrupt"  : "Unknown",
}

# ── Fuzzy match threshold ─────────────────────────────────────
FUZZY_THRESHOLD = 80

# ── Fallback when no reason code matches ─────────────────────
REASON_ACTION_DEFAULT = ("Unclassified shortfall", "Manual review required")