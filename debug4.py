# debug4.py — tests all files using the correct parser
import os, config

# Point at test data BEFORE importing parsers
config.EXCEL_CLAIMS = r"D:\Medical Aid\TestData\Test_Client_Data.xlsx"

import parsers

folder = r"D:\Medical Aid\TestData"

files = [
    ("alliance_cimas_test_recon.pdf",  parsers.parse_alliance, "CIMAS test"),
    ("alliance_fmh_test_recon.pdf",    parsers.parse_alliance, "FMH test"),
    ("alliance_ruth_test_recon.pdf",   parsers.parse_alliance, "Alliance/Ruth test"),
    ("alliance_bonvie_test_recon.pdf", parsers.parse_alliance, "Bonvie test"),
]

for fname, parser_fn, label in files:
    path = os.path.join(folder, fname)
    print(f"\n=== {label} ({fname}) ===")
    try:
        txs = parser_fn(path)
        for t in txs:
            print(f"  invoice=[{t['invoice_num']}] patient=[{t['patient_name']}] "
                  f"member_id=[{t.get('member_id','')}] "
                  f"claimed={t['claimed_amt']} accepted={t['accepted_amt']} "
                  f"shortfall={t['shortfall_amt']} reason=[{t['reason_code']}]")
        if not txs:
            print("  (no transactions parsed)")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n=== EXCEL CLAIMS ===")
claims = parsers.load_excel_claims()
for c in claims:
    print(f"  payer={c['payer']:10} ref=[{c['claim_ref']}] "
          f"member=[{c['member_name']}] num=[{c['member_number']}] "
          f"date={c['visit_date']}")