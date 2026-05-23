# =============================================================
# config.py  —  All settings for the Medical Aid Recon Bot
# =============================================================

import os

# ── Folders ───────────────────────────────────────────────────
INTAKE_FOLDER    = r"D:\Medical Aid\Files"
PROCESSED_FOLDER = r"D:\Medical Aid\Files\Processed"
OUTPUT_FOLDER    = r"D:\Medical Aid\Files\Output"
EXCEL_CLAIMS     = r"D:\Medical Aid\Files\Client Data.xlsx"

# ── Reason codes config file ──────────────────────────────────
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