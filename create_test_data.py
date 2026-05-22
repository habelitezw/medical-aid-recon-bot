# =============================================================
# create_test_data.py
# Run once to generate test Excel + test PDF remittances
# covering ALL output tab scenarios.
# Usage: python create_test_data.py
# Output: D:\Medical Aid\TestData\
# =============================================================

import os
import openpyxl
from openpyxl.styles import Font, PatternFill
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

OUT_DIR = r"D:\Medical Aid\TestData"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Test scenarios ─────────────────────────────────────────────────────────────
# We create 10 claims in the Excel and matching remittance lines designed to hit:
#   Tab 2 (Fully Reconciled)     : 3 claims paid in full
#   Tab 3 (Shortfalls for Action): 4 claims with shortfalls (various reasons)
#   Tab 4 (Unmatched - PDF)      : 2 remittance lines with no Excel match
#   Tab 4 (Unmatched - Excel)    : 2 Excel claims with no remittance
#   Tab 5 (Error Log)            : triggered by a corrupt PDF (we'll note this)
#   Tab 6 (Action Tracker)       : auto-populated from Tab 3

EXCEL_CLAIMS = [
    # (date, payer, member_name, member_number, claim_ref, claimed, phone)
    # ── Will match + fully reconciled ────────────────────────────────────────
    (date(2026,3,1),  "CIMAS",   "John Moyo",     "CIMAS-001", "0931-99001-11111-AA1", 50.00,  "+263771000001"),
    (date(2026,3,5),  "CIMAS",   "Mary Dube",     "CIMAS-002", "0931-99002-22222-BB2", 70.00,  "+263771000002"),
    (date(2026,3,10), "FMH",     "Peter Ncube",   "FMH-001",   "0931-99003-33333-CC3", 80.00,  "+263771000003"),
    # ── Will match + shortfall: tariff difference ─────────────────────────────
    (date(2026,3,12), "CIMAS",   "Grace Mutasa",  "CIMAS-003", "0931-99004-44444-DD4", 60.00,  "+263771000004"),
    # ── Will match + shortfall: benefit exhausted ─────────────────────────────
    (date(2026,3,15), "FMH",     "Tafara Choto",  "FMH-002",   "0931-99005-55555-EE5", 50.00,  "+263771000005"),
    # ── Will match + shortfall: not covered ──────────────────────────────────
    (date(2026,3,18), "ALLIANCE","Ruth Banda",    "ALI-001",   "",                    80.00,  "+263771000006"),
    # ── Will match + shortfall: data error ───────────────────────────────────
    (date(2026,3,20), "CIMAS",   "David Sithole", "CIMAS-004", "0931-99007-77777-GG7", 50.00,  "+263771000007"),
    # ── No remittance — Excel unmatched ──────────────────────────────────────
    (date(2026,3,22), "CIMAS",   "Agnes Mokoena", "CIMAS-005", "0931-99008-88888-HH8", 70.00,  "+263771000008"),
    (date(2026,3,25), "FMH",     "Brian Mwale",   "FMH-003",   "0931-99009-99999-II9", 50.00,  "+263771000009"),
    # ── Member number match (no invoice) ─────────────────────────────────────
    (date(2026,3,28), "BONVIE",  "Clara Osei",    "BON-001",   "",                    60.00,  "+263771000010"),
]

# ── Build Excel ────────────────────────────────────────────────────────────────

def build_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Client Data"

    headers = [
        "Date", "Col2", "Col3", "Col4", "Col5", "Col6",
        "Surname", "First Name", "Col9", "Col10", "Col11",
        "Payer", "Medical Aid Number", "Col14",
        "Primary Medical Aid Member",
        "Col16","Col17","Col18","Col19","Col20",
        "Col21","Col22","Col23","Col24","Col25",
        "Col26","Col27",
        "NH263 Claim reference",
        "MEDICAL AID Amount claimed USD",
        "Col30","Col31",
        "Medical Aid Amount remitted USD",
        "Medical Aid Discrepancy USD",
        "Col34","Col35",
        "Medical Aid          Reason for discrepancy",
        "Claim Status",
        "Patient ID ",
        "Phone Number",
    ]
    ws.append(headers)
    hfill = PatternFill("solid", fgColor="1F4E79")
    hfont = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = hfill
        cell.font = hfont

    # Pre-fill remitted/discrepancy for claims that WILL match
    # (the bot overwrites unmatched ones with 0)
    remitted_map = {
        "0931-99001-11111-AA1": (50.00, 0.00,  "Paid in full"),
        "0931-99002-22222-BB2": (70.00, 0.00,  "Paid in full"),
        "0931-99003-33333-CC3": (80.00, 0.00,  "Paid in full"),
        "0931-99004-44444-DD4": (54.00, 6.00,  "Partial"),
        "0931-99005-55555-EE5": (40.00, 10.00, "Partial"),
        "0931-99007-77777-GG7": (50.00, 0.00,  "Pending"),
    }

    for i, (dt, payer, member, mem_num, ref, claimed, phone) in enumerate(EXCEL_CLAIMS, 2):
        remitted, disc, status = remitted_map.get(ref, (0.0, 0.0, "Pending"))
        row = [""] * len(headers)
        row[0]  = dt
        row[11] = payer
        row[12] = mem_num
        row[14] = member
        row[27] = ref
        row[28] = claimed
        row[31] = remitted
        row[32] = disc
        row[36] = status
        row[38] = phone
        ws.append(row)

    out = os.path.join(OUT_DIR, "Test_Client_Data.xlsx")
    wb.save(out)
    print(f"  Created: {out}")
    return out


# ── Build PDFs ─────────────────────────────────────────────────────────────────

styles = getSampleStyleSheet()

def _make_pdf(filename, aid_name, payment_ref, rows, reason_codes):
    """
    rows: list of dicts with keys:
      member_name, member_id, patient_name, date, invoice,
      code, claimed, accepted, shortfall, reason_code
    reason_codes: dict {code: description}
    """
    path  = os.path.join(OUT_DIR, filename)
    doc   = SimpleDocTemplate(path, pagesize=A4,
                              leftMargin=15*mm, rightMargin=15*mm,
                              topMargin=15*mm, bottomMargin=15*mm)
    elems = []
    normal = styles["Normal"]
    title  = styles["Heading1"]

    elems.append(Paragraph(f"{aid_name}", title))
    elems.append(Paragraph(f"Claims Remittance Advice", styles["Heading2"]))
    elems.append(Paragraph(f"Payment Reference: {payment_ref}   Date: 2026/03/31", normal))
    elems.append(Spacer(1, 6*mm))
    elems.append(Paragraph("Provider: WASHAYA JENNIFER (19097)", normal))
    elems.append(Spacer(1, 4*mm))

    # Flatten rows by member
    current_member = None
    table_data = [
        ["Treatment Date", "Invoice Number", "Code", "Qty",
         "Claimed", "Accepted", "Shortfall", "Prev Paid",
         "Pay To You", "Pay To Member", "Reason"]
    ]

    for r in rows:
        if r["member_name"] != current_member:
            current_member = r["member_name"]
            table_data.append([
                f"Treatment Details: Member : {r['member_name']} ({r['member_id']})  "
                f"Patient : {r['patient_name']}",
                "", "", "", "", "", "", "", "", "", ""
            ])
        table_data.append([
            r["date"], r["invoice"], r["code"], "1",
            f"{r['claimed']:.2f}", f"{r['accepted']:.2f}",
            f"{r['shortfall']:.2f}", "0.00",
            f"{r['accepted']:.2f}", "0.00",
            r.get("reason_code", "")
        ])

    col_w = [22*mm, 38*mm, 14*mm, 8*mm,
             16*mm, 16*mm, 16*mm, 14*mm,
             16*mm, 16*mm, 10*mm]

    t = Table(table_data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTSIZE",    (0,0), (-1,-1), 7),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1),
         [colors.HexColor("#f7fbff"), colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.25, colors.grey),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 6*mm))

    if reason_codes:
        elems.append(Paragraph("Reasons explained", styles["Heading3"]))
        rc_data = [["Reason", "Description"]]
        for code, desc in reason_codes.items():
            rc_data.append([code, desc])
        rt = Table(rc_data, colWidths=[20*mm, 150*mm])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DEEAF1")),
            ("FONTSIZE",   (0,0), (-1,-1), 7),
            ("GRID",       (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        elems.append(rt)

    doc.build(elems)
    print(f"  Created: {path}")


def build_pdfs():
    # ── Cimas: 3 fully reconciled + 2 shortfalls + 1 unmatched PDF line
    _make_pdf(
        filename    = "cimas_test_recon.pdf",
        aid_name    = "Cimas Medical Aid",
        payment_ref = "CIMAS-EFT-2026031",
        rows=[
            # Fully reconciled
            dict(member_name="John Moyo",    member_id="CIMAS-001",
                 patient_name="John Moyo",   date="01/03/2026",
                 invoice="0931-99001-11111-AA1", code="90030",
                 claimed=50.00, accepted=50.00, shortfall=0.00),
            dict(member_name="Mary Dube",    member_id="CIMAS-002",
                 patient_name="Mary Dube",   date="05/03/2026",
                 invoice="0931-99002-22222-BB2", code="90030",
                 claimed=70.00, accepted=70.00, shortfall=0.00),
            # Shortfall: tariff difference (reason code 6)
            dict(member_name="Grace Mutasa", member_id="CIMAS-003",
                 patient_name="Grace Mutasa", date="12/03/2026",
                 invoice="0931-99004-44444-DD4", code="67228",
                 claimed=60.00, accepted=54.00, shortfall=6.00,
                 reason_code="6"),
            # Shortfall: data error (reason code 40)
            dict(member_name="David Sithole",member_id="CIMAS-004",
                 patient_name="David Sithole",date="20/03/2026",
                 invoice="0931-99007-77777-GG7", code="90030",
                 claimed=50.00, accepted=0.00, shortfall=50.00,
                 reason_code="40"),
            # Unmatched PDF line (no Excel entry for this patient)
            dict(member_name="Unregistered Patient", member_id="CIMAS-999",
                 patient_name="Unregistered Patient", date="25/03/2026",
                 invoice="0931-99099-99999-ZZ9", code="90030",
                 claimed=50.00, accepted=50.00, shortfall=0.00),
        ],
        reason_codes={"6": "Amount claimed exceeds tariff amount",
                      "40": "Duplicate claim — already processed"}
    )

    # ── FMH: 1 fully reconciled + 1 shortfall (benefit exhausted) + 1 unmatched
    _make_pdf(
        filename    = "fmh_test_recon.pdf",
        aid_name    = "First Mutual Health",
        payment_ref = "FMH-EFT-20260331",
        rows=[
            # Fully reconciled
            dict(member_name="Peter Ncube",  member_id="FMH-001",
                 patient_name="Peter Ncube", date="10/03/2026",
                 invoice="0931-99003-33333-CC3", code="90030",
                 claimed=80.00, accepted=80.00, shortfall=0.00),
            # Shortfall: benefit exhausted (reason code D)
            dict(member_name="Tafara Choto", member_id="FMH-002",
                 patient_name="Tafara Choto",date="15/03/2026",
                 invoice="0931-99005-55555-EE5", code="92021",
                 claimed=50.00, accepted=40.00, shortfall=10.00,
                 reason_code="D"),
            # Unmatched: appears on remittance but not in Excel
            dict(member_name="Unknown Member",member_id="FMH-999",
                 patient_name="Unknown Member",date="29/03/2026",
                 invoice="0931-99099-88888-YY8", code="90030",
                 claimed=60.00, accepted=60.00, shortfall=0.00),
        ],
        reason_codes={"D": "Benefits exhausted"}
    )

    # ── Alliance: 1 shortfall (not covered) — matched by member number
    _make_pdf(
        filename    = "alliance_test_recon.pdf",
        aid_name    = "Alliance Health",
        payment_ref = "ALI-EFT-20260401",
        rows=[
            dict(member_name="Ruth Banda",   member_id="ALI-001",
                 patient_name="Ruth Banda",  date="18/03/2026",
                 invoice="",  code="66826",
                 claimed=80.00, accepted=0.00, shortfall=80.00,
                 reason_code="E"),
        ],
        reason_codes={"E": "Not a covered benefit under this plan"}
    )

    # ── Bonvie: matched by member number (no invoice in Excel)
    _make_pdf(
        filename    = "bonvie_test_recon.pdf",
        aid_name    = "Bonvie",
        payment_ref = "BON-BATCH-20260219",
        rows=[
            dict(member_name="Clara Osei",   member_id="BON-001",
                 patient_name="Clara Osei",  date="28/03/2026",
                 invoice="424999",  code="66826",
                 claimed=60.00, accepted=60.00, shortfall=0.00),
        ],
        reason_codes={}
    )


if __name__ == "__main__":
    print("Installing reportlab if needed...")
    os.system("pip install reportlab --quiet --break-system-packages 2>nul")

    print("\nGenerating test data...")
    build_excel()
    build_pdfs()

    print(f"\nDone. Test files are in: {OUT_DIR}")
    print("\nTo test:")
    print("  1. Open the web app at http://localhost:5000")
    print("  2. Upload Test_Client_Data.xlsx")
    print("  3. Upload all 4 PDF files")
    print("  4. Download and open the RECON output")
    print("  5. All 6 tabs should have data")