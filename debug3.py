# debug3.py
import pdfplumber
import os

folder = r"D:\Medical Aid\TestData"
for fname in ["cimas_test_recon.pdf", "alliance_test_recon.pdf"]:
    path = os.path.join(folder, fname)
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- PAGE {i+1} ---")
            tables = page.extract_tables()
            print(f"Tables found: {len(tables)}")
            for j, t in enumerate(tables):
                print(f"  Table {j+1}: {len(t)} rows")
                for row in t[:4]:
                    print(f"    {row}")