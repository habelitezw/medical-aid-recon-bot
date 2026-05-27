# diag_new.py
import pdfplumber, os

files = {
    "GEN_HEALTH" : r"D:\Medical Aid\Files\25 FEB 2026 GEN HEALTH ZIG MBIDZENI MATSIKA CONSULTATION.pdf",
    "MAISHA"     : r"D:\Medical Aid\Files\2026 MARCH 5 MAISHA USD GETRUDE CHIFAMBA AND STEPHEN MUNAZVO.pdf",
    "ALLIANCE2"  : r"D:\Medical Aid\Files\27 FEB 2026 ALLIANCE USD YANAI, TONDERAI , YEVEDZO GWANGWAWA.pdf",
}

for label, path in files.items():
    print(f"\n{'='*60}")
    print(f"FILE: {label}")
    print(f"{'='*60}")
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- PAGE {i+1} ---")
            tables = page.extract_tables()
            print(f"Tables found: {len(tables)}")
            for j, t in enumerate(tables):
                print(f"  Table {j+1}: {len(t)} rows")
                for row in t[:4]:
                    print(f"    {row}")
            print("RAW TEXT (first 1200 chars):")
            txt = page.extract_text()
            if txt:
                print(txt[:1200])
        if i == 0:
            break