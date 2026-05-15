# =============================================================
# app.py  —  Flask web interface for Medical Aid Recon Bot
# Run with:  python app.py
# Then open: http://localhost:5000
# =============================================================

import os
import shutil
import uuid
from datetime import datetime
from flask import (Flask, render_template, request,
                   send_file, redirect, url_for, flash)

from parsers import parse_remittance, load_excel_claims
from recon_bot import build_output, _match_by_invoice, _match_by_name_date
from config import MEDICAL_AID_MAP

app = Flask(__name__)
app.secret_key = "habelite-recon-2026"

# ── Working folders (relative to app.py location) ────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR   = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _identify_medical_aid(filename):
    """Return canonical medical aid name from filename."""
    name = filename.lower()
    for key, label in MEDICAL_AID_MAP.items():
        if key in name:
            return label
    return "Unknown"


def _run_recon(session_dir, excel_path, pdf_paths):
    """
    Core reconciliation logic — same as recon_bot.run() but
    operates on uploaded files and returns the output file path.
    """
    # Temporarily override the Excel path in parsers
    import parsers
    original_excel = parsers.EXCEL_CLAIMS
    parsers.EXCEL_CLAIMS = excel_path

    try:
        # Load Excel claims
        excel_claims = load_excel_claims()

        # Parse each PDF
        all_transactions = []
        error_log = []
        match_log = []

        for pdf_path in pdf_paths:
            filename = os.path.basename(pdf_path)
            medical_aid = _identify_medical_aid(filename)
            try:
                txs = parse_remittance(pdf_path, medical_aid)
                all_transactions.extend(txs)
            except Exception as e:
                error_log.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    filename, str(e)
                ])

        # Match transactions
        for tx in all_transactions:
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
                match_log.append({"match_method": method,
                                  "invoice": tx.get("invoice_num", ""),
                                  "patient": tx.get("patient_name", "")})
            else:
                tx["matched"]      = False
                tx["match_method"] = "unmatched"

        # Build output workbook
        run_date = datetime.now()
        wb = build_output(run_date, all_transactions,
                          excel_claims, match_log, error_log)

        out_name = f"RECON_{run_date.strftime('%Y%m%d_%H%M%S')}_ALL.xlsx"
        out_path = os.path.join(session_dir, out_name)
        wb.save(out_path)
        return out_path, len(all_transactions), len(excel_claims), len(match_log), error_log

    finally:
        parsers.EXCEL_CLAIMS = original_excel


# ── Routes ────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_recon():
    # Validate uploads
    excel_file = request.files.get("excel_file")
    pdf_files  = request.files.getlist("pdf_files")

    if not excel_file or excel_file.filename == "":
        flash("Please upload the Client Data Excel file.", "error")
        return redirect(url_for("index"))

    if not pdf_files or all(f.filename == "" for f in pdf_files):
        flash("Please upload at least one remittance PDF.", "error")
        return redirect(url_for("index"))

    # Create a unique session folder for this run
    session_id  = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        # Save Excel
        excel_path = os.path.join(session_dir, "Client_Data.xlsx")
        excel_file.save(excel_path)

        # Save PDFs
        pdf_paths = []
        for pdf in pdf_files:
            if pdf.filename == "":
                continue
            safe_name = pdf.filename.replace(" ", "_")
            pdf_path  = os.path.join(session_dir, safe_name)
            pdf.save(pdf_path)
            pdf_paths.append(pdf_path)

        # Run reconciliation
        out_path, n_pdf, n_excel, n_matched, errors = _run_recon(
            session_dir, excel_path, pdf_paths)

        # Send the file back as a download
        return send_file(
            out_path,
            as_attachment=True,
            download_name=os.path.basename(out_path),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        flash(f"An error occurred during reconciliation: {str(e)}", "error")
        return redirect(url_for("index"))

    finally:
        # Clean up session folder after a delay is not possible in sync Flask,
        # so we clean up OLD sessions (> 1 hour) on each new run instead
        _cleanup_old_sessions()


def _cleanup_old_sessions():
    """Delete session folders older than 1 hour."""
    import time
    cutoff = time.time() - 3600
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if os.path.isdir(path):
            try:
                if os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path)
            except Exception:
                pass


if __name__ == "__main__":
    # debug=False for production; change host to "0.0.0.0" to allow
    # access from other devices on the same network
    app.run(debug=False, host="0.0.0.0", port=5000)