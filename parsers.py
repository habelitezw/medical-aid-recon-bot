# =============================================================
# parsers.py  —  PDF and Excel readers for each medical aid
# Supports: FMH, Cimas, FLIMAS, Bonvie, CellMed, Alliance
# =============================================================

import os
import re
import pdfplumber
import pandas as pd
from datetime import datetime
from config import (EXCEL_CLAIMS, COL_DATE, COL_PAYER, COL_MEMBER_NAME,
                    COL_MEMBER_NUMBER, COL_CLAIM_REF, COL_CLAIMED_USD,
                    COL_REMITTED_USD, COL_DISCREPANCY, COL_REASON,
                    COL_STATUS, COL_PATIENT_ID, COL_PHONE)


# ── Helpers ───────────────────────────────────────────────────

def _safe_float(val):
    """Convert a value to float, return 0.0 on failure."""
    try:
        cleaned = str(val).replace(",", "").replace("$", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0

def _safe_date(val):
    """Parse various date formats into a date object, or return None."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d",
                "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y",
                "%b %d, %Y", "%d-%m-%y", "%m-%d-%Y",
                "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

# ── Member ID extractor ───────────────────────────────────────

# Patterns for Zimbabwean medical aid member numbers
_MEMBER_ID_PATTERNS = [
    re.compile(r'\b(\d{8,12}[A-Z]?)\b'),        # 8-12 digit numeric, optional letter suffix
    re.compile(r'\b([A-Z]{2,4}\d{6,10})\b'),    # 2-4 letters then digits (e.g. BA12088U)
    re.compile(r'\b(\d{10}:\d{2})\b'),           # Bonvie format e.g. 2012283261:00
    re.compile(r'\b([A-Z0-9]{6,12}[UN]\d*)\b'),  # ends in N or U (Alliance style)
]

def _extract_member_id(text: str) -> str:
    """
    Extract a member ID from a cell that may contain both
    the member name and ID together, e.g:
      'WONDER MADYAMBUDZI (322403002N)'
      '322403002N Wonder Madyambudzi'
      'MR EBENEZER GUMBO (14088113)'
    Returns the first match found, or empty string.
    """
    if not text:
        return ""
    # First check inside parentheses — most common format
    paren = re.findall(r'\(([^)]+)\)', text)
    for p in paren:
        p = p.strip()
        for pattern in _MEMBER_ID_PATTERNS:
            m = pattern.search(p)
            if m:
                return m.group(1)
    # Then scan the full text
    for pattern in _MEMBER_ID_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return ""

# ── Excel reader ──────────────────────────────────────────────

def load_excel_claims():
    """
    Load Client Data.xlsx and return a list of claim dicts.
    Only rows where Payer is not CASH are included.
    """
    df = pd.read_excel(EXCEL_CLAIMS, sheet_name="Client Data",
                       engine="openpyxl", dtype=str)
    df.columns = df.columns.str.strip()

    claims = []
    for _, row in df.iterrows():
        payer = str(row.get(COL_PAYER, "")).strip().upper()
        if payer in ("CASH", "NAN", ""):
            continue

        claim_ref = str(row.get(COL_CLAIM_REF, "")).strip()
        if claim_ref in ("nan", "Cash Settlement", "Cash Settlement ",
                         "Probono: EGI", "Manual Claim", "0", ""):
            claim_ref = ""

        raw_date = row.get(COL_DATE, "")
        try:
            visit_date = pd.to_datetime(raw_date).date()
        except Exception:
            visit_date = _safe_date(raw_date)

        claims.append({
            "source"      : "excel",
            "payer"       : payer,
            "member_name" : str(row.get(COL_MEMBER_NAME, "")).strip(),
            "claim_ref"   : claim_ref,
            "visit_date"  : visit_date,
            "claimed_usd" : _safe_float(row.get(COL_CLAIMED_USD, 0)),
            "remitted_usd": _safe_float(row.get(COL_REMITTED_USD, 0)),
            "discrepancy" : _safe_float(row.get(COL_DISCREPANCY, 0)),
            "reason"      : str(row.get(COL_REASON, "")).strip(),
            "status"      : str(row.get(COL_STATUS, "")).strip(),
            "patient_id"  : str(row.get(COL_PATIENT_ID, "")).strip(),
            "member_number": str(row.get(COL_MEMBER_NUMBER, "")).strip().upper(),
            "phone"        : str(row.get(COL_PHONE, "")).strip(),
            "matched"     : False,
        })
    return claims


# ── Shared: text-based parser for FMH / Cimas / FLIMAS ───────
#
# These three aids share the same PDF layout:
#   - Each transaction row is split across two text lines because
#     the invoice number wraps (e.g. "0931-11357-" on line 1,
#     "25079-D94" on line 2)
#   - Member/patient header lines appear as:
#     "Treatment Details: Member : NAME (ID) Patient : NAME"
#   - Reason code table at the bottom: "Reason  Description"
#
# Strategy: extract raw text, walk line by line.

def _parse_text_based(pdf_path, medical_aid_name, has_claim_number=False,
                      has_tax_column=False):
    """
    Generic text-based parser for FMH, Cimas, and FLIMAS.

    The invoice number in these PDFs is split across two lines:
      Line 1: DATE  0931-11357-  CODE  QTY  AMOUNTS...
      Line 2: 25079-D94

    Strategy: parse the data row on line 1 immediately (the amounts
    are all there), then use line 2 to patch the invoice suffix onto
    the last parsed transaction.
    """
    transactions = []
    reason_map   = {}

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"

    lines = full_text.splitlines()

    # ── Pass 1: build reason code map from footer ─────────────
    in_reasons = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^reasons\s+explained", stripped, re.IGNORECASE):
            in_reasons = True
            continue
        if re.match(r"^statement\s+columns\s+explained", stripped, re.IGNORECASE):
            in_reasons = False
            continue
        if in_reasons:
            if re.match(r"^(Reason|Description)\s*$", stripped, re.IGNORECASE):
                continue
            m = re.match(r"^(\S+)\s{2,}(.+)$", stripped)
            if m:
                codes_part = m.group(1).strip()
                desc       = m.group(2).strip()
                for code in re.split(r"[,\s]+", codes_part):
                    code = code.strip()
                    if code:
                        reason_map[code] = desc

    # ── Pass 2: extract transaction rows ──────────────────────
    current_member  = ""
    current_patient = ""

    date_re = re.compile(r"^(\d{2}[/\-]\d{2}[/\-]\d{2,4})\s+(.+)$")

    # An invoice suffix line is ONLY an alphanumeric/dash token — nothing else
    # e.g. "25079-D94" or "39771-AA0" or "38338-5E5" or "44985-41B"
    suffix_re = re.compile(r"^([A-Z0-9][\w\-]+)$", re.IGNORECASE)

    member_re = re.compile(
        r"treatment\s+details.*?member\s*[:\-]\s*(.+?)\s+patient\s*[:\-]\s*(.+)",
        re.IGNORECASE)

    skip_re = re.compile(
        r"^(sub\s+totals?|statement\s+totals?|provider\s+balances?|"
        r"opening\s+balance|closing\s+balance|claims\s+processed|"
        r"payment\s*\(|withh?old|see\s+the\s+end|provider\s*:|"
        r"treatment\s+invoice|claims\s+remittance|page\s+\d|"
        r"reasons?\s+explained|reason\s+description|statement\s+columns)",
        re.IGNORECASE)

    def _parse_row(date_str, rest, member, patient):
        parts = rest.split()
        if len(parts) < 4:
            return None

        invoice = parts[0]

        # For Cimas: parts[1] is a claim number (skip it)
        if has_claim_number and len(parts) >= 6:
            idx = 2
        else:
            idx = 1

        if idx >= len(parts):
            return None

        tariff_code = parts[idx]; idx += 1
        idx += 1  # skip qty

        claimed   = _safe_float(parts[idx]) if idx < len(parts) else 0.0; idx += 1
        accepted  = _safe_float(parts[idx]) if idx < len(parts) else 0.0; idx += 1
        shortfall = _safe_float(parts[idx]) if idx < len(parts) else 0.0; idx += 1
        idx += 1  # skip previously paid
        pay_you   = _safe_float(parts[idx]) if idx < len(parts) else 0.0; idx += 1
        idx += 1  # skip pay to member
        if has_tax_column:
            idx += 1  # skip tax
        reason_code = parts[idx].strip() if idx < len(parts) else ""
        if len(reason_code) > 10:
            reason_code = ""

        treat_date = _safe_date(date_str)
        if treat_date is None:
            return None

        # shortfall can also be derived if not present
        if shortfall == 0.0 and claimed != accepted:
            shortfall = round(claimed - accepted, 2)

        reason_desc = reason_map.get(reason_code, "")
        if not reason_desc and reason_code:
            reason_desc = f"Reason code {reason_code} (see remittance)"

        # Try to extract member ID from member name or patient name
        # in case it's embedded e.g. "MR JOHN DOE (14088113)"
        extracted_id = (
            _extract_member_id(member) or
            _extract_member_id(patient)
        )

        return {
            "source"        : "pdf",
            "medical_aid"   : medical_aid_name,
            "member_name"   : member,
            "patient_name"  : patient,
            "member_id"     : extracted_id,
            "treat_date"    : treat_date,
            "invoice_num"   : invoice,
            "tariff_code"   : tariff_code,
            "claimed_amt"   : claimed,
            "accepted_amt"  : accepted,
            "shortfall_amt" : shortfall,
            "pay_to_you"    : pay_you,
            "reason_code"   : reason_code,
            "reason_desc"   : reason_desc,
            "matched"       : False,
        }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Member/patient header
        m = member_re.search(stripped)
        if m:
            raw_member  = m.group(1).strip()
            raw_patient = m.group(2).strip()
            current_member  = re.sub(r"\s*\(\d+\)\s*$", "", raw_member).strip()
            current_patient = re.sub(r"\s*\(\d+\)\s*$", "", raw_patient).strip()
            continue

        if skip_re.match(stripped):
            continue

        # Invoice suffix line — patch the last transaction's invoice number
        # These lines are ONLY the suffix token, nothing else
        sm = suffix_re.match(stripped)
        if sm and transactions:
            last = transactions[-1]
            if last["invoice_num"].endswith("-"):
                last["invoice_num"] = last["invoice_num"] + sm.group(1)
            continue

        # Data row starting with a date
        dm = date_re.match(stripped)
        if dm:
            tx = _parse_row(dm.group(1), dm.group(2),
                            current_member, current_patient)
            if tx:
                transactions.append(tx)
            continue

    return transactions

# ── FMH parser ────────────────────────────────────────────────

def parse_fmh(pdf_path):
    return _parse_text_based(
        pdf_path,
        medical_aid_name="First Mutual Health",
        has_claim_number=False,
        has_tax_column=False
    )


# ── Cimas parser ──────────────────────────────────────────────

def parse_cimas(pdf_path):
    return _parse_text_based(
        pdf_path,
        medical_aid_name="Cimas",
        has_claim_number=True,
        has_tax_column=True
    )


# ── FLIMAS parser ─────────────────────────────────────────────

def parse_flimas(pdf_path):
    return _parse_text_based(
        pdf_path,
        medical_aid_name="FLIMAS",
        has_claim_number=False,
        has_tax_column=True
    )


# ── Bonvie parser ─────────────────────────────────────────────
#
# Table-based. Table 2 contains the data rows.
# Columns: Treatment Date | Invoice Number | Code | Qty |
#          Claimed Amount | Awarded Amount | Pay To You |
#          Pay By Member | Tax Amount | Reason
# Note: no explicit Shortfall column — calculate from claimed - awarded.
# Amounts prefixed with "$ " — _safe_float handles this.

def parse_bonvie(pdf_path):
    transactions = []
    reason_map   = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            # Build reason map from "Reasons explained" table
            for table in tables:
                if not table:
                    continue
                flat = " ".join(str(c) for c in table[0] if c).lower()
                if "reason" in flat and "description" in flat:
                    for row in table[1:]:
                        if row and len(row) >= 2 and row[0] and row[1]:
                            reason_map[str(row[0]).strip()] = str(row[1]).strip()

            current_member  = ""
            current_patient = ""

            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = [str(c).strip().lower() if c else ""
                          for c in table[0]]
                # Bonvie main table has "treatment\ndate" in header
                if not any("treatment" in h for h in header):
                    continue

                for row in table[1:]:
                    if not row:
                        continue
                    row_s = [str(c).strip() if c else "" for c in row]
                    joined = " ".join(row_s)

                    # Member header row
                    m = re.search(
                        r"treatment\s+details.*?member\s*[-:]\s*(.+?)\s+patient\s*[-:]\s*(.+)",
                        joined, re.IGNORECASE)
                    if m:
                        raw_member  = m.group(1).strip()
                        raw_patient = m.group(2).strip()
                        current_member  = re.sub(
                            r"\s*\([\w:]+\)\s*", "", raw_member).strip()
                        current_patient = re.sub(
                            r"\s*\([\w:]+\)\s*", "", raw_patient).strip()
                        continue

                    # Skip sub-total / statement total rows
                    if any(x in joined.lower() for x in
                           ["sub total", "statement total"]):
                        continue

                    # Data row: col 0 = date
                    treat_date = _safe_date(row_s[0])
                    if treat_date is None:
                        continue

                    invoice    = row_s[1] if len(row_s) > 1 else ""
                    tariff     = row_s[2] if len(row_s) > 2 else ""
                    claimed    = _safe_float(row_s[4]) if len(row_s) > 4 else 0.0
                    awarded    = _safe_float(row_s[5]) if len(row_s) > 5 else 0.0
                    pay_you    = _safe_float(row_s[6]) if len(row_s) > 6 else 0.0
                    shortfall  = round(claimed - awarded, 2)
                    reason_code = row_s[9] if len(row_s) > 9 else ""
                    reason_desc = reason_map.get(reason_code, "")
                    if not reason_desc and reason_code and reason_code != "0":
                        reason_desc = f"Reason code {reason_code} (see remittance)"

                    extracted_id = (
                        _extract_member_id(current_member) or
                        _extract_member_id(current_patient) or
                        _extract_member_id(row_s[1] if len(row_s) > 1 else "")
                    )

                    transactions.append({
                        "source"        : "pdf",
                        "member_id"     : extracted_id,
                        "member_name"   : current_member,
                        "patient_name"  : current_patient,
                        "treat_date"    : treat_date,
                        "invoice_num"   : invoice,
                        "tariff_code"   : tariff,
                        "claimed_amt"   : claimed,
                        "accepted_amt"  : awarded,
                        "shortfall_amt" : shortfall,
                        "pay_to_you"    : pay_you,
                        "reason_code"   : reason_code,
                        "reason_desc"   : reason_desc,
                        "matched"       : False,
                    })

    return transactions


# ── CellMed parser ────────────────────────────────────────────
#
# Table-based. Table 1 on page 1 contains all data rows.
# Columns: Treatment Date | Invoice Number | Code | Qty |
#          Claimed Amount | Accepted Amount | Previously Paid |
#          Pay To You | Pay To Member | Tax Amount | Reason
# Reason can be multi-code: "409, 416"
# Member header format:
#   "Treatment Details: Member: NAME (ID) - Currency: USD - Patient: NAME"

def parse_cellmed(pdf_path):
    transactions = []
    reason_map   = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            # Reason map — page 2 table
            for table in tables:
                if not table:
                    continue
                flat = " ".join(str(c) for c in (table[0] or []) if c).lower()
                if "reason" in flat and ("explained" in flat or "description" in flat):
                    for row in table[1:]:
                        if row and len(row) >= 2 and row[0] and row[1]:
                            reason_map[str(row[0]).strip()] = str(row[1]).strip()

            current_member  = ""
            current_patient = ""

            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = [str(c).strip().lower() if c else ""
                          for c in table[0]]
                if not any("treatment" in h for h in header):
                    continue

                for row in table[1:]:
                    if not row:
                        continue
                    row_s = [str(c).strip() if c else "" for c in row]
                    joined = " ".join(row_s)

                    # Member header — CellMed uses "Member:" (no space before colon)
                    # and separates patient with " - Patient:"
                    m = re.search(
                        r"treatment\s+details.*?member\s*:\s*(.+?)\s*-\s*currency.*?-\s*patient\s*:\s*(.+)",
                        joined, re.IGNORECASE)
                    if m:
                        raw_member  = m.group(1).strip()
                        raw_patient = m.group(2).strip()
                        current_member  = re.sub(r"\s*\([\d\s]+\)\s*", "",
                                                 raw_member).strip()
                        current_patient = raw_patient.strip()
                        continue

                    if any(x in joined.lower() for x in
                           ["sub total", "statement total"]):
                        continue

                    treat_date = _safe_date(row_s[0])
                    if treat_date is None:
                        continue

                    invoice     = row_s[1] if len(row_s) > 1 else ""
                    tariff      = row_s[2] if len(row_s) > 2 else ""
                    claimed     = _safe_float(row_s[4]) if len(row_s) > 4 else 0.0
                    accepted    = _safe_float(row_s[5]) if len(row_s) > 5 else 0.0
                    pay_you     = _safe_float(row_s[7]) if len(row_s) > 7 else 0.0
                    shortfall   = round(claimed - accepted, 2)
                    reason_code = row_s[10] if len(row_s) > 10 else ""

                    # Build combined description for multi-code reasons
                    reason_parts = []
                    for code in re.split(r"[,\s]+", reason_code):
                        code = code.strip()
                        if code and code in reason_map:
                            reason_parts.append(f"{code}: {reason_map[code]}")
                    reason_desc = " | ".join(reason_parts) if reason_parts else (
                        f"Reason code(s) {reason_code} (see remittance)"
                        if reason_code else "")

                    extracted_id = (
                        _extract_member_id(current_member) or
                        _extract_member_id(current_patient) or
                        _extract_member_id(row_s[1] if len(row_s) > 1 else "")
                    )

                    transactions.append({
                        "source"        : "pdf",
                        "medical_aid"   : "CellMed",
                        "member_name"   : current_member,
                        "patient_name"  : current_patient,
                        "member_id"     : extracted_id,
                        "treat_date"    : treat_date,
                        "invoice_num"   : invoice,
                        "tariff_code"   : tariff,
                        "claimed_amt"   : claimed,
                        "accepted_amt"  : accepted,
                        "shortfall_amt" : shortfall,
                        "pay_to_you"    : pay_you,
                        "reason_code"   : reason_code,
                        "reason_desc"   : reason_desc,
                        "matched"       : False,
                    })

    return transactions


# ── Alliance parser ───────────────────────────────────────────
#
# Table-based. The main data table is Table 1 (8+ rows).
# Row 0: notice text (skip)
# Row 1: EFT number header (skip)
# Row 2: column headers
# Row 3+: data rows
#
# The "Member Name" column is split across two cells due to a
# merged None cell — we handle this by joining adjacent cells.

def parse_alliance(pdf_path):
    """
    Parse an Alliance Health payment notice PDF.
    Works with both real Alliance PDFs (which have a None merged cell
    in the Member Name column) and synthetic test PDFs (which don't).
    """
    transactions = []
    sf_map       = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            # Build shortfall code description map
            for table in tables:
                if not table:
                    continue
                h = [str(c).strip().lower() if c else ""
                     for c in table[0]]
                if "shortfall code" in h and "shortfall description" in h:
                    for row in table[1:]:
                        if row and len(row) >= 2 and row[0] and row[1]:
                            sf_map[str(row[0]).strip()] = str(row[1]).strip()

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Find header row containing "claim date"
                header_row_idx = None
                for idx, row in enumerate(table):
                    if row and any("claim date" in str(c).lower()
                                   for c in row if c):
                        header_row_idx = idx
                        break
                if header_row_idx is None:
                    continue

                # Build header list — collapse None cells into
                # the previous header (handles merged cells)
                raw_header = table[header_row_idx]
                header = []
                last   = ""
                for c in raw_header:
                    val = str(c).strip().lower().replace("\n", " ") if c else ""
                    if val:
                        last = val
                        header.append(val)
                    else:
                        # None/empty = merged cell, repeat previous
                        header.append(last + "_merged")

                def col_idx(name):
                    for i, h in enumerate(header):
                        if name.lower() in h:
                            return i
                    return None

                idx_date      = col_idx("claim date")
                idx_claimno   = col_idx("claimno")
                idx_memberid  = col_idx("memberid")
                idx_claimed   = col_idx("claimed")
                idx_award     = col_idx("award")
                idx_shortfall = col_idx("shortfall amount") or col_idx("shortfall")
                idx_sfcode    = col_idx("shortfall code")
                idx_diagnosis = col_idx("diagnosis")
                idx_invoice   = col_idx("invoice")
                idx_patient   = col_idx("patient")

                # Member name: collect cells between memberid and patient
                def get_member_name(row):
                    if idx_memberid is None or idx_patient is None:
                        return ""
                    parts = []
                    for i in range(idx_memberid + 1, idx_patient):
                        v = str(row[i]).strip() if i < len(row) and row[i] else ""
                        # Skip if it matches a known header keyword
                        if v and not any(kw in v.lower() for kw in
                                         ["member", "patient", "claimed",
                                          "award", "shortfall", "diagnosis"]):
                            parts.append(v)
                    return " ".join(parts)

                def g(row, idx):
                    if idx is None or idx >= len(row):
                        return ""
                    return str(row[idx]).strip() if row[idx] else ""

                for row in table[header_row_idx + 1:]:
                    if not row:
                        continue
                    row_s = [str(c).strip() if c else "" for c in row]

                    treat_date = _safe_date(g(row_s, idx_date))
                    if treat_date is None:
                        continue

                    claimed   = _safe_float(g(row_s, idx_claimed))
                    awarded   = _safe_float(g(row_s, idx_award))
                    sf_amt = _safe_float(g(row_s, idx_shortfall))
                    # Always derive shortfall from claimed - awarded
                    # to avoid column-shift errors in synthetic PDFs
                    if claimed > 0 and awarded >= 0:
                        sf_amt = round(claimed - awarded, 2)
                    sf_amt = max(sf_amt, 0.0)  # never negative

                    _raw_reason = g(row_s, idx_sfcode)
                    reason_code = _raw_reason.replace("[", "").replace("]", "").strip()
                    reason_desc = sf_map.get(reason_code, "")
                    if not reason_desc and reason_code:
                        reason_desc = f"ShortFall code {reason_code} (see remittance)"

                    tariff_col  = col_idx("afhoz")
                    tariff_code = g(row_s, tariff_col) if tariff_col else ""

                    member_name = get_member_name(row_s)
                    patient     = g(row_s, idx_patient)

                    # If member name is empty, fall back to patient name
                    if not member_name:
                        member_name = patient

                    # Extract member ID from any cell that might contain it
                    # Handles cases where member ID is embedded in name cell
                    # e.g. "WONDER MADYAMBUDZI (322403002N)" or blacked-out columns
                    extracted_member_id = (
                        _extract_member_id(member_name) or
                        _extract_member_id(patient) or
                        _extract_member_id(g(row_s, idx_memberid))
                    )

                    transactions.append({
                        "source"        : "pdf",
                        "medical_aid"   : "Alliance Health",
                        "member_name"   : member_name,
                        "patient_name"  : patient,
                        "member_id"     : extracted_member_id or g(row_s, idx_memberid),
                        "treat_date"    : treat_date,
                        "invoice_num"   : g(row_s, idx_invoice),
                        "tariff_code"   : tariff_code,
                        "claimed_amt"   : claimed,
                        "accepted_amt"  : awarded,
                        "shortfall_amt" : sf_amt,
                        "pay_to_you"    : awarded,
                        "reason_code"   : reason_code,
                        "reason_desc"   : reason_desc,
                        "claim_no"      : g(row_s, idx_claimno),
                        "diagnosis"     : g(row_s, idx_diagnosis),
                        "matched"       : False,
                    })

    return transactions

# ── Dispatcher ────────────────────────────────────────────────

def parse_remittance(pdf_path, medical_aid_name):
    """Route to the correct parser based on medical aid name.
    NOTE: alliance must be checked BEFORE cimas/fmh/bonvie because
    test filenames may contain both keywords e.g. alliance_cimas_test.pdf
    """
    name = medical_aid_name.lower()
    if "alliance" in name:
        return parse_alliance(pdf_path)
    elif "first mutual" in name or "fmh" in name:
        return parse_fmh(pdf_path)
    elif "cimas" in name:
        return parse_cimas(pdf_path)
    elif "flimas" in name:
        return parse_flimas(pdf_path)
    elif "bonvie" in name:
        return parse_bonvie(pdf_path)
    elif "cellmed" in name:
        return parse_cellmed(pdf_path)
    else:
        raise ValueError(
            f"No parser configured for medical aid: '{medical_aid_name}'. "
            f"File: {os.path.basename(pdf_path)}. "
            f"Add this aid to MEDICAL_AID_MAP in config.py and implement a parser."
        )
    """Route to the correct parser based on medical aid name."""
    name = medical_aid_name.lower()
    if "first mutual" in name or "fmh" in name:
        return parse_fmh(pdf_path)
    elif "cimas" in name:
        return parse_cimas(pdf_path)
    elif "flimas" in name:
        return parse_flimas(pdf_path)
    elif "bonvie" in name:
        return parse_bonvie(pdf_path)
    elif "cellmed" in name:
        return parse_cellmed(pdf_path)
    elif "alliance" in name:
        return parse_alliance(pdf_path)
    else:
        # Unknown aid — attempt Alliance-style parse then raise
        # so the error gets logged in the Error Log tab
        raise ValueError(
            f"No parser configured for medical aid: '{medical_aid_name}'. "
            f"File: {os.path.basename(pdf_path)}. "
            f"Add this aid to MEDICAL_AID_MAP in config.py and implement a parser."
        )