# =============================================================
# config.py  —  All settings for the Medical Aid Recon Bot
# Edit this file when folders change or new medical aids are added
# =============================================================

import os

# ── Folders ───────────────────────────────────────────────────
INTAKE_FOLDER    = r"D:\Medical Aid\Files"
PROCESSED_FOLDER = r"D:\Medical Aid\Files\Processed"
OUTPUT_FOLDER    = r"D:\Medical Aid\Files\Output"
EXCEL_CLAIMS     = r"D:\Medical Aid\Files\Client Data.xlsx"

# ── Excel column names (must match Client Data.xlsx header row)
COL_DATE          = "Date"
COL_PAYER         = "Payer"
COL_MEMBER_NAME   = "Primary Medical Aid Member"
COL_CLAIM_REF     = "NH263 Claim reference"
COL_CLAIMED_USD   = "MEDICAL AID Amount claimed USD"
COL_REMITTED_USD  = "Medical Aid Amount remitted USD"
COL_DISCREPANCY   = "Medical Aid Discrepancy USD"
COL_REASON        = "Medical Aid          Reason for discrepancy"
COL_STATUS        = "Claim Status"
COL_PATIENT_ID    = "Patient ID "
COL_PHONE         = "Phone Number"

# ── Medical aid name mapping
# Key = string that appears in the PDF filename (case-insensitive)
# Value = canonical name used in output
MEDICAL_AID_MAP = {
    "alliance" : "Alliance Health",
    "bonvie"   : "Bonvie",
    "cellmed"  : "CellMed",
    "cimas"    : "Cimas",
    "flimas"   : "FLIMAS",
    "fmh"      : "First Mutual Health",
    "psmas"    : "PSMAS",
}

# ── Fuzzy match threshold (0-100). Lower = more lenient.
# 80 is a good starting point; raise to 85 if you get false matches
FUZZY_THRESHOLD = 80

# ── Shortfall action rules
# Maps reason code keywords to action classification
# These cover FMH and Alliance; extend as other aids are added
REASON_ACTION_MAP = [
    # (keyword_in_reason_description,        classification,                    action)
    ("exceeds tariff",   "Tariff difference",      "Assess: write off or bill patient for difference"),
    ("tariff",           "Tariff difference",      "Assess: write off or bill patient for difference"),
    ("benefit",          "Benefit exhausted",      "Contact patient — patient liable for shortfall"),
    ("exhausted",        "Benefit exhausted",      "Contact patient — patient liable for shortfall"),
    ("not covered",      "Not a covered benefit",  "Contact patient — patient liable for full amount"),
    ("not a benefit",    "Not a covered benefit",  "Contact patient — patient liable for full amount"),
    ("incorrect",        "Data/submission error",  "Correct claim and resubmit"),
    ("error",            "Data/submission error",  "Correct claim and resubmit"),
    ("wrong",            "Data/submission error",  "Correct claim and resubmit"),
    ("date",             "Data/submission error",  "Correct claim and resubmit"),
    ("member id",        "Data/submission error",  "Correct claim and resubmit"),
]

# Fallback when no keyword matches
REASON_ACTION_DEFAULT = ("Unclassified shortfall", "Manual review required")