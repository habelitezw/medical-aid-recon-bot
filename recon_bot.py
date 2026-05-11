# =============================================================
# recon_bot.py  —  Main reconciliation bot
# Run with:  python recon_bot.py
# =============================================================

import os
import shutil
import logging
from datetime import datetime, date

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (PatternFill, Font, Alignment,
                              Border, Side)
from openpyxl.utils import get_column_letter
from thefuzz import fuzz

from config import (INTAKE_FOLDER, PROCESSED_FOLDER, OUTPUT_FOLDER,
                    MEDICAL_AID_MAP, FUZZY_THRESHOLD,
                    REASON_ACTION_MAP, REASON_ACTION_DEFAULT)
from parsers import parse_remittance, load_excel_claims


# ── Logging setup ─────────────────────────────────────────────
os.makedirs(OUTPUT_FOLDER,    exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

log_path = os.path.join(OUTPUT_FOLDER,
    f"recon_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ── Styling helpers ───────────────────────────────────────────
HEADER_FILL    = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT    = Font(bold=True, color="FFFFFF", size=10)
GREEN_FILL     = PatternFill("solid", fgColor="E2EFDA")
AMBER_FILL     = PatternFill("solid", fgColor="FFF2CC")
RED_FILL       = PatternFill("solid", fgColor="FCE4D6")
BLUE_FILL      = PatternFill("solid", fgColor="DEEAF1")
THIN_BORDER    = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"))

def _style_header(ws, row_num, col_count):
    for c in range(1, col_count + 1):
        cell = ws.cell(row=row_num, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = THIN_BORDER

def _auto_width(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                max_len = max(max_len, len(str(cell.value or "")))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 4, 45)


# ── Matching logic ────────────────────────────────────────────

def _normalise(s):
    return str(s).strip().upper().replace("  ", " ")

def _match_by_invoice(pdf_tx, excel_claims):
    """Exact match on invoice/claim reference number."""
    inv = _normalise(pdf_tx.get("invoice_num", ""))
    if not inv or inv in ("", "NAN"):
        return None
    for claim in excel_claims:
        if not claim["matched"] and _normalise(claim["claim_ref"]) == inv:
            return claim
    return None

def _match_by_name_date(pdf_tx, excel_claims):
    """Fuzzy name + exact date match as fallback."""
    pdf_name = _normalise(pdf_tx.get("patient_name", "")
                          or pdf_tx.get("member_name", ""))
    pdf_date = pdf_tx.get("treat_date")
    if not pdf_name or not pdf_date:
        return None

    best_score  = 0
    best_claim  = None
    for claim in excel_claims:
        if claim["matched"]:
            continue
        if claim["visit_date"] != pdf_date:
            continue
        score = fuzz.token_sort_ratio(pdf_name,
                                      _normalise(claim["member_name"]))
        if score > best_score:
            best_score = score
            best_claim = claim

    if best_score >= FUZZY_THRESHOLD:
        return best_claim
    return None


# ── Action classification ─────────────────────────────────────

def _classify_action(shortfall_amt, reason_desc):
    if shortfall_amt == 0:
        return "Fully reconciled", "No action required", GREEN_FILL

    desc_lower = (reason_desc or "").lower()
    for keyword, classification, action in REASON_ACTION_MAP:
        if keyword in desc_lower:
            fill = AMBER_FILL if "tariff" in classification.lower() else RED_FILL
            return classification, action, fill

    cls, act = REASON_ACTION_DEFAULT
    return cls, act, AMBER_FILL


# ── Output builder ────────────────────────────────────────────

def _add_sheet(wb, name):
    ws = wb.create_sheet(name)
    return ws

def build_output(run_date, pdf_transactions, excel_claims,
                 match_log, error_log):

    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    # ── Tab 1: Summary ────────────────────────────────────────
    ws_sum = _add_sheet(wb, "1 - Summary")
    summary_data = [
        ["Medical Aid Reconciliation — Run Summary", ""],
        ["Run date",          run_date.strftime("%d %B %Y %H:%M")],
        [""],
        ["TOTALS", ""],
        ["PDF transactions parsed",    len(pdf_transactions)],
        ["Excel claims loaded",        len(excel_claims)],
        ["Matched (invoice)",          sum(1 for m in match_log if m["match_method"] == "invoice")],
        ["Matched (name + date)",      sum(1 for m in match_log if m["match_method"] == "fuzzy")],
        ["Unmatched PDF lines",        sum(1 for t in pdf_transactions if not t["matched"])],
        ["Unmatched Excel claims",     sum(1 for c in excel_claims    if not c["matched"])],
        [""],
        ["SHORTFALL SUMMARY", ""],
        ["Total shortfall value (USD)",
            round(sum(t["shortfall_amt"] for t in pdf_transactions), 2)],
        ["Fully reconciled (no shortfall)",
            sum(1 for t in pdf_transactions if t["shortfall_amt"] == 0 and t["matched"])],
        ["Shortfalls requiring action",
            sum(1 for t in pdf_transactions if t["shortfall_amt"] > 0 and t["matched"])],
        [""],
        ["Errors encountered",         len(error_log)],
    ]
    for r, row in enumerate(summary_data, 1):
        for c, val in enumerate(row, 1):
            cell = ws_sum.cell(row=r, column=c, value=val)
            if r == 1:
                cell.font = Font(bold=True, size=14, color="1F4E79")
            elif val in ("TOTALS", "SHORTFALL SUMMARY"):
                cell.font = Font(bold=True, size=11)
                cell.fill = BLUE_FILL
    ws_sum.column_dimensions["A"].width = 35
    ws_sum.column_dimensions["B"].width = 25

    # ── Tab 2: Fully Reconciled ───────────────────────────────
    ws_rec = _add_sheet(wb, "2 - Fully Reconciled")
    rec_headers = ["Medical Aid", "Patient Name", "Member Name",
                   "Treatment Date", "Invoice Number", "Tariff Code",
                   "Claimed (USD)", "Accepted (USD)", "Shortfall (USD)",
                   "Pay To You", "Match Method"]
    ws_rec.append(rec_headers)
    _style_header(ws_rec, 1, len(rec_headers))

    for tx in pdf_transactions:
        if tx["shortfall_amt"] == 0 and tx["matched"]:
            row = [
                tx.get("medical_aid", ""),
                tx.get("patient_name", ""),
                tx.get("member_name", ""),
                str(tx.get("treat_date", "")),
                tx.get("invoice_num", ""),
                tx.get("tariff_code", ""),
                tx.get("claimed_amt", 0),
                tx.get("accepted_amt", 0),
                0,
                tx.get("pay_to_you", 0),
                tx.get("match_method", ""),
            ]
            r = ws_rec.max_row + 1
            ws_rec.append(row)
            for c in range(1, len(rec_headers) + 1):
                ws_rec.cell(r, c).fill   = GREEN_FILL
                ws_rec.cell(r, c).border = THIN_BORDER
    _auto_width(ws_rec)

    # ── Tab 3: Shortfalls for Action ─────────────────────────
    ws_sf = _add_sheet(wb, "3 - Shortfalls for Action")
    sf_headers = ["Medical Aid", "Patient Name", "Member Name",
                  "Treatment Date", "Invoice Number", "Tariff Code",
                  "Claimed (USD)", "Accepted (USD)", "Shortfall (USD)",
                  "Reason Code", "Reason Description",
                  "Classification", "Action Required",
                  "Patient Phone", "Match Method"]
    ws_sf.append(sf_headers)
    _style_header(ws_sf, 1, len(sf_headers))

    for tx in pdf_transactions:
        if tx["shortfall_amt"] > 0 and tx["matched"]:
            cls, action, fill = _classify_action(
                tx["shortfall_amt"], tx.get("reason_desc", ""))
            row = [
                tx.get("medical_aid", ""),
                tx.get("patient_name", ""),
                tx.get("member_name", ""),
                str(tx.get("treat_date", "")),
                tx.get("invoice_num", ""),
                tx.get("tariff_code", ""),
                tx.get("claimed_amt", 0),
                tx.get("accepted_amt", 0),
                tx.get("shortfall_amt", 0),
                tx.get("reason_code", ""),
                tx.get("reason_desc", ""),
                cls,
                action,
                tx.get("phone", ""),
                tx.get("match_method", ""),
            ]
            r = ws_sf.max_row + 1
            ws_sf.append(row)
            for c in range(1, len(sf_headers) + 1):
                ws_sf.cell(r, c).fill   = fill
                ws_sf.cell(r, c).border = THIN_BORDER
    _auto_width(ws_sf)

    # ── Tab 4: Unmatched Records ──────────────────────────────
    ws_um = _add_sheet(wb, "4 - Unmatched Records")
    um_headers = ["Source", "Medical Aid", "Patient / Member Name",
                  "Treatment Date", "Invoice Number",
                  "Claimed (USD)", "Shortfall (USD)",
                  "Possible Reason", "Notes"]
    ws_um.append(um_headers)
    _style_header(ws_um, 1, len(um_headers))

    for tx in pdf_transactions:
        if not tx["matched"]:
            r = ws_um.max_row + 1
            ws_um.append([
                "PDF remittance",
                tx.get("medical_aid", ""),
                tx.get("patient_name", "") or tx.get("member_name", ""),
                str(tx.get("treat_date", "")),
                tx.get("invoice_num", ""),
                tx.get("claimed_amt", 0),
                tx.get("shortfall_amt", 0),
                "Claim not found in Client Data.xlsx",
                "Check if patient was recorded or claim was submitted",
            ])
            for c in range(1, len(um_headers) + 1):
                ws_um.cell(r, c).fill   = AMBER_FILL
                ws_um.cell(r, c).border = THIN_BORDER

    for claim in excel_claims:
        if not claim["matched"]:
            r = ws_um.max_row + 1
            ws_um.append([
                "Excel claim record",
                claim.get("payer", ""),
                claim.get("member_name", ""),
                str(claim.get("visit_date", "")),
                claim.get("claim_ref", ""),
                claim.get("claimed_usd", 0),
                "",
                "No remittance line found for this claim",
                "Claim may not yet be processed by medical aid, or was not submitted",
            ])
            for c in range(1, len(um_headers) + 1):
                ws_um.cell(r, c).fill   = RED_FILL
                ws_um.cell(r, c).border = THIN_BORDER
    _auto_width(ws_um)

    # ── Tab 5: Error Log ──────────────────────────────────────
    ws_err = _add_sheet(wb, "5 - Error Log")
    err_headers = ["Timestamp", "File", "Error"]
    ws_err.append(err_headers)
    _style_header(ws_err, 1, len(err_headers))
    for entry in error_log:
        ws_err.append(entry)
    _auto_width(ws_err)

    # ── Tab 6: Action Tracker ─────────────────────────────────
    ws_at = _add_sheet(wb, "6 - Action Tracker")
    at_headers = ["Status", "Medical Aid", "Patient Name", "Member Name",
                  "Treatment Date", "Invoice Number",
                  "Shortfall (USD)", "Reason Description",
                  "Classification", "Action Required",
                  "Patient Phone", "Date Actioned", "Notes"]
    ws_at.append(at_headers)
    _style_header(ws_at, 1, len(at_headers))

    for tx in pdf_transactions:
        if tx["shortfall_amt"] > 0 and tx["matched"]:
            cls, action, fill = _classify_action(
                tx["shortfall_amt"], tx.get("reason_desc", ""))
            r = ws_at.max_row + 1
            ws_at.append([
                "Open",
                tx.get("medical_aid", ""),
                tx.get("patient_name", ""),
                tx.get("member_name", ""),
                str(tx.get("treat_date", "")),
                tx.get("invoice_num", ""),
                tx.get("shortfall_amt", 0),
                tx.get("reason_desc", ""),
                cls,
                action,
                tx.get("phone", ""),
                "",   # Date Actioned — staff fill this in
                "",   # Notes — staff fill this in
            ])
            for c in range(1, len(at_headers) + 1):
                cell = ws_at.cell(r, c)
                cell.border = THIN_BORDER
                if c == 1:  # Status column
                    cell.fill = AMBER_FILL
                    cell.font = Font(bold=True)
    _auto_width(ws_at)
    # Freeze the header row on the Action Tracker
    ws_at.freeze_panes = "A2"

    return wb


# ── Main bot logic ────────────────────────────────────────────

def run():
    run_start  = datetime.now()
    error_log  = []
    match_log  = []

    log.info("=" * 60)
    log.info("Medical Aid Reconciliation Bot — START")
    log.info(f"Intake folder : {INTAKE_FOLDER}")
    log.info(f"Output folder : {OUTPUT_FOLDER}")
    log.info("=" * 60)

    # 1. Load Excel claims
    log.info("Loading Client Data.xlsx ...")
    try:
        excel_claims = load_excel_claims()
        log.info(f"  Loaded {len(excel_claims)} medical aid claim records")
    except Exception as e:
        log.error(f"FATAL: Cannot load Client Data.xlsx — {e}")
        return

    # 2. Scan intake folder for PDFs
    pdf_files = [f for f in os.listdir(INTAKE_FOLDER)
                 if f.lower().endswith(".pdf")]
    log.info(f"Found {len(pdf_files)} PDF file(s) in intake folder")

    if not pdf_files:
        log.warning("No PDF files found. Nothing to process.")
        return

    # 3. Parse each PDF
    all_pdf_transactions = []
    processed_files      = []

    for filename in pdf_files:
        pdf_path = os.path.join(INTAKE_FOLDER, filename)
        log.info(f"  Processing: {filename}")

        # Identify medical aid from filename
        medical_aid_name = "Unknown"
        for key, name in MEDICAL_AID_MAP.items():
            if key in filename.lower():
                medical_aid_name = name
                break

        try:
            transactions = parse_remittance(pdf_path, medical_aid_name)
            log.info(f"    Parsed {len(transactions)} transaction lines")
            all_pdf_transactions.extend(transactions)
            processed_files.append((filename, pdf_path))
        except Exception as e:
            msg = f"Error parsing {filename}: {e}"
            log.error(f"    {msg}")
            error_log.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                filename, str(e)
            ])

    # 4. Match each PDF transaction to an Excel claim
    log.info("Matching transactions to Excel claims ...")
    for tx in all_pdf_transactions:
        claim = _match_by_invoice(tx, excel_claims)
        method = "invoice"
        if claim is None:
            claim = _match_by_name_date(tx, excel_claims)
            method = "fuzzy"

        if claim is not None:
            tx["matched"]      = True
            tx["match_method"] = method
            tx["phone"]        = claim.get("phone", "")
            claim["matched"]   = True
            match_log.append({
                "match_method" : method,
                "invoice"      : tx.get("invoice_num", ""),
                "patient"      : tx.get("patient_name", ""),
            })
            log.info(f"    MATCH ({method}): {tx.get('invoice_num', '')} "
                     f"— {tx.get('patient_name', '')}")
        else:
            tx["matched"]      = False
            tx["match_method"] = "unmatched"
            log.warning(f"    NO MATCH: {tx.get('invoice_num', '')} "
                        f"— {tx.get('patient_name', '')} "
                        f"on {tx.get('treat_date', '')}")

    # 5. Build output workbook
    log.info("Building reconciliation output workbook ...")
    wb = build_output(run_start, all_pdf_transactions,
                      excel_claims, match_log, error_log)

    out_name = f"RECON_{run_start.strftime('%Y%m%d_%H%M%S')}_ALL.xlsx"
    out_path = os.path.join(OUTPUT_FOLDER, out_name)
    wb.save(out_path)
    log.info(f"  Output saved: {out_path}")

    # 6. Archive processed PDFs
    log.info("Archiving processed PDF files ...")
    dated_archive = os.path.join(
        PROCESSED_FOLDER,
        run_start.strftime("%Y%m%d"))
    os.makedirs(dated_archive, exist_ok=True)

    for filename, pdf_path in processed_files:
        dest = os.path.join(dated_archive, filename)
        shutil.move(pdf_path, dest)
        log.info(f"  Archived: {filename} → {dated_archive}")

    # 7. Final summary
    run_end = datetime.now()
    duration = (run_end - run_start).seconds
    log.info("=" * 60)
    log.info("RECONCILIATION COMPLETE")
    log.info(f"  Duration          : {duration}s")
    log.info(f"  PDF transactions  : {len(all_pdf_transactions)}")
    log.info(f"  Excel claims      : {len(excel_claims)}")
    log.info(f"  Matched           : {len(match_log)}")
    log.info(f"  Unmatched PDF     : {sum(1 for t in all_pdf_transactions if not t['matched'])}")
    log.info(f"  Unmatched Excel   : {sum(1 for c in excel_claims if not c['matched'])}")
    log.info(f"  Errors            : {len(error_log)}")
    log.info(f"  Output file       : {out_name}")
    log.info("=" * 60)


if __name__ == "__main__":
    run()