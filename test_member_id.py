# test_member_id.py — verify member ID extraction from text
from parsers import _extract_member_id, parse_fmh, parse_alliance
import os
import sys

print("=== Member ID extraction tests ===")
tests = [
    ("MR EBENEZER GUMBO (14088113)",          "14088113"),
    ("MISS VICTORIA MUKASA-BATENDE (10931968)","10931968"),
    ("Wonder Madyambudzi (322403002N)",        "322403002N"),
    ("MRS MABLE MATIZANHAU (2012283261:00)",   "2012283261:00"),
    ("MRS PERPETUA MAKOSA ( 2014589366 )",     "2014589366"),
    ("MR STANFORD CHIDEME (2024571912)",       "2024571912"),
    ("Plain Name No ID",                       ""),
]

all_passed = True
for text, expected in tests:
    result = _extract_member_id(text)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_passed = False
    print(f"  {status} [{text[:45]:45}] -> [{result}] (expected [{expected}])")

print()
print("All tests passed ✓" if all_passed else "Some tests FAILED ✗")

print()
print("=== FMH real PDF member IDs ===")
fmh_path = r"D:\Medical Aid\Files\Processed\20260511\FMH 210126.pdf"
if os.path.exists(fmh_path):
    txs = parse_fmh(fmh_path)
    for t in txs:
        print(f"  patient=[{t['patient_name']}] "
              f"member_id=[{t.get('member_id','')}] "
              f"invoice=[{t['invoice_num']}]")
else:
    print(f"  FMH PDF not found at {fmh_path}")
    print("  (move it back from Processed folder to test with real data)")

if not all_passed:
    sys.exit(1)
