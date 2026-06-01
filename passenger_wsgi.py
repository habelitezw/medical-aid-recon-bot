import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_RELEASE_FILE = os.path.join(BASE_DIR, ".current-release")

with open(CURRENT_RELEASE_FILE, encoding="utf-8") as release_file:
    release_id = release_file.read().strip()

if not re.fullmatch(r"[a-f0-9]{40}", release_id):
    raise RuntimeError("Invalid active release")

RELEASE_DIR = os.path.join(BASE_DIR, "releases", release_id)
VENDOR_DIR = os.path.join(RELEASE_DIR, "vendor")

if VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)
if RELEASE_DIR not in sys.path:
    sys.path.insert(0, RELEASE_DIR)

os.chdir(RELEASE_DIR)

from app import app as application
