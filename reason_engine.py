# =============================================================
# reason_engine.py  —  Loads and applies configurable reason codes
# =============================================================

import json
import re
from config import REASON_CODES_FILE, REASON_ACTION_DEFAULT


def load_reason_codes():
    """Load reason codes from JSON file. Returns list of code dicts."""
    try:
        with open(REASON_CODES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("codes", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_reason_codes(codes):
    """Save reason codes list back to JSON file."""
    with open(REASON_CODES_FILE, "w", encoding="utf-8") as f:
        json.dump({"codes": codes}, f, indent=2, ensure_ascii=False)


def get_all_medical_aids():
    """Return sorted list of unique medical aid names from code list."""
    codes = load_reason_codes()
    aids  = sorted(set(c["medical_aid"] for c in codes))
    return aids


def lookup_reason(reason_code, medical_aid, pdf_description=""):
    """
    Look up a reason code and return (description, classification, action, fill_colour).

    Lookup order:
      1. Exact match on code + medical_aid
      2. Exact match on code + "ALL"
      3. Keyword match on pdf_description against known descriptions
      4. Default fallback
    """
    if not reason_code and not pdf_description:
        return "", "Fully reconciled", "No action required", "GREEN"

    codes = load_reason_codes()
    code_str = str(reason_code).strip()

    # Split multi-code strings e.g. "409, 416"
    code_parts = [c.strip() for c in re.split(r"[,\s]+", code_str) if c.strip()]

    results = []
    for part in code_parts:
        matched = None
        # 1. Exact match on this aid
        for entry in codes:
            if (entry["code"].strip() == part and
                    entry["medical_aid"].upper() == medical_aid.upper()):
                matched = entry
                break
        # 2. Fallback to ALL
        if not matched:
            for entry in codes:
                if (entry["code"].strip() == part and
                        entry["medical_aid"].upper() == "ALL"):
                    matched = entry
                    break
        if matched:
            results.append(matched)

    if results:
        # Combine multiple codes
        desc    = " | ".join(r["description"]     for r in results)
        cls     = " | ".join(r["classification"]  for r in results)
        action  = results[0]["action"]  # use first action
        colour  = _classification_to_colour(results[0]["classification"])
        return desc, cls, action, colour

    # 3. Keyword match on pdf_description
    if pdf_description:
        desc_lower = pdf_description.lower()
        keyword_map = [
            (["exceeds tariff", "tariff"],
             "Tariff difference",
             "Assess: write off or bill patient for difference", "AMBER"),
            (["exhausted", "benefit used", "no units"],
             "Benefit exhausted",
             "Contact patient — patient liable for shortfall amount", "RED"),
            (["not covered", "not a benefit", "exclusion", "excluded"],
             "Not a covered benefit",
             "Contact patient — patient liable for full amount", "RED"),
            (["duplicate", "already processed"],
             "Duplicate / submission error",
             "Review claim records — do not resubmit", "AMBER"),
            (["error", "incorrect", "wrong", "invalid", "date"],
             "Data / submission error",
             "Correct the error and resubmit", "AMBER"),
            (["co-payment", "co payment", "levy", "discount"],
             "Scheme exclusion / co-payment",
             "Contact patient — patient liable for shortfall amount", "AMBER"),
        ]
        for keywords, cls, action, colour in keyword_map:
            if any(kw in desc_lower for kw in keywords):
                return pdf_description, cls, action, colour

    # 4. Default
    cls, action = REASON_ACTION_DEFAULT
    return pdf_description or f"Code {reason_code}", cls, action, "AMBER"


def _classification_to_colour(classification):
    cls = classification.lower()
    if "tariff" in cls or "error" in cls or "duplicate" in cls or "co-payment" in cls:
        return "AMBER"
    if "exhausted" in cls or "not covered" in cls or "exclusion" in cls:
        return "RED"
    return "AMBER"