# =============================================================
# app.py  —  Flask web interface for Medical Aid Recon Bot
# =============================================================

import os
import shutil
import uuid
import json
from datetime import datetime
from flask import (Flask, render_template, request, send_file,
                   redirect, url_for, flash, jsonify)

from parsers import parse_remittance, load_excel_claims
from recon_bot import build_output, _match_by_invoice, \
                     _match_by_member_number, _match_by_name_date
from reason_engine import (load_reason_codes, save_reason_codes,
                           get_all_medical_aids, lookup_reason)
from config import MEDICAL_AID_MAP, REASON_CODES_FILE

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "habelite-recon-2026")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "habelite2026")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _identify_medical_aid(filename):
    name = filename.lower()
    for key, label in MEDICAL_AID_MAP.items():
        if key in name:
            return label
    return "Unknown"


def _run_recon(session_dir, excel_path, pdf_paths):
    import parsers
    original = parsers.EXCEL_CLAIMS
    parsers.EXCEL_CLAIMS = excel_path
    try:
        excel_claims     = load_excel_claims()
        all_transactions = []
        error_log        = []
        match_log        = []

        for pdf_path in pdf_paths:
            filename    = os.path.basename(pdf_path)
            medical_aid = _identify_medical_aid(filename)
            try:
                txs = parse_remittance(pdf_path, medical_aid)
                all_transactions.extend(txs)
            except Exception as e:
                error_log.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    filename, str(e)])

        for tx in all_transactions:
            claim, method = _match_by_invoice(tx, excel_claims)
            if claim is None:
                claim, method = _match_by_member_number(tx, excel_claims)
            if claim is None:
                claim, method = _match_by_name_date(tx, excel_claims)

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

        run_date = datetime.now()
        wb       = build_output(run_date, all_transactions,
                                excel_claims, match_log, error_log)
        out_name = f"RECON_{run_date.strftime('%Y%m%d_%H%M%S')}_ALL.xlsx"
        out_path = os.path.join(session_dir, out_name)
        wb.save(out_path)
        return out_path, len(all_transactions), len(excel_claims), \
               len(match_log), error_log
    finally:
        parsers.EXCEL_CLAIMS = original


def _cleanup_old_sessions():
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


# ── Main upload page ──────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_recon():
    excel_file = request.files.get("excel_file")
    pdf_files  = request.files.getlist("pdf_files")

    if not excel_file or excel_file.filename == "":
        flash("Please upload the Client Data Excel file.", "error")
        return redirect(url_for("index"))
    if not pdf_files or all(f.filename == "" for f in pdf_files):
        flash("Please upload at least one remittance PDF.", "error")
        return redirect(url_for("index"))

    session_id  = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        excel_path = os.path.join(session_dir, "Client_Data.xlsx")
        excel_file.save(excel_path)

        pdf_paths = []
        for pdf in pdf_files:
            if pdf.filename == "":
                continue
            safe_name = pdf.filename.replace(" ", "_")
            pdf_path  = os.path.join(session_dir, safe_name)
            pdf.save(pdf_path)
            pdf_paths.append(pdf_path)

        out_path, *_ = _run_recon(session_dir, excel_path, pdf_paths)
        return send_file(
            out_path,
            as_attachment=True,
            download_name=os.path.basename(out_path),
            mimetype="application/vnd.openxmlformats-officedocument"
                     ".spreadsheetml.sheet")
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for("index"))
    finally:
        _cleanup_old_sessions()


# ── Reason Code Manager ───────────────────────────────────────

@app.route("/codes", methods=["GET"])
def codes_page():
    """Main reason code manager page — requires admin login."""
    if not _is_admin():
        return redirect(url_for("admin_login"))
    codes = load_reason_codes()
    aids  = sorted(set(list(MEDICAL_AID_MAP.values()) + ["ALL"]))
    classifications = [
        "Tariff difference",
        "Benefit exhausted",
        "Not a covered benefit",
        "Data / submission error",
        "Duplicate / submission error",
        "Scheme exclusion / co-payment",
        "Unclassified shortfall",
    ]
    return render_template("codes.html",
                           codes=codes,
                           aids=aids,
                           classifications=classifications)


@app.route("/codes/add", methods=["POST"])
def codes_add():
    if not _is_admin():
        return redirect(url_for("admin_login"))
    codes = load_reason_codes()
    codes.append({
        "code"           : request.form.get("code", "").strip().upper(),
        "medical_aid"    : request.form.get("medical_aid", "ALL"),
        "description"    : request.form.get("description", "").strip(),
        "classification" : request.form.get("classification", "").strip(),
        "action"         : request.form.get("action", "").strip(),
    })
    save_reason_codes(codes)
    flash("Reason code added successfully.", "success")
    return redirect(url_for("codes_page"))


@app.route("/codes/delete/<int:index>", methods=["POST"])
def codes_delete(index):
    if not _is_admin():
        return redirect(url_for("admin_login"))
    codes = load_reason_codes()
    if 0 <= index < len(codes):
        codes.pop(index)
        save_reason_codes(codes)
        flash("Reason code deleted.", "success")
    return redirect(url_for("codes_page"))


@app.route("/codes/edit/<int:index>", methods=["POST"])
def codes_edit(index):
    if not _is_admin():
        return redirect(url_for("admin_login"))
    codes = load_reason_codes()
    if 0 <= index < len(codes):
        codes[index] = {
            "code"           : request.form.get("code", "").strip().upper(),
            "medical_aid"    : request.form.get("medical_aid", "ALL"),
            "description"    : request.form.get("description", "").strip(),
            "classification" : request.form.get("classification", "").strip(),
            "action"         : request.form.get("action", "").strip(),
        }
        save_reason_codes(codes)
        flash("Reason code updated.", "success")
    return redirect(url_for("codes_page"))


# ── Admin auth ────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == ADMIN_PASSWORD:
            from flask import session
            session["admin"] = True
            return redirect(url_for("codes_page"))
        flash("Incorrect password.", "error")
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    from flask import session
    session.pop("admin", None)
    return redirect(url_for("index"))


def _is_admin():
    from flask import session
    return session.get("admin") is True


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)