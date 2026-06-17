import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_RELEASE_FILE = os.path.join(BASE_DIR, ".current-release")
PROJECT_ROOT = BASE_DIR

if os.path.isfile(CURRENT_RELEASE_FILE):
    with open(CURRENT_RELEASE_FILE, encoding="utf-8") as release_file:
        release_id = release_file.read().strip()

    if not re.fullmatch(r"[a-f0-9]{40}", release_id):
        raise RuntimeError("Invalid active release")

    release_dir = os.path.join(BASE_DIR, "releases", release_id)
    vendor_dir = os.path.join(release_dir, "vendor")

    if os.path.isdir(vendor_dir) and vendor_dir not in sys.path:
        sys.path.insert(0, vendor_dir)
    if os.path.isdir(release_dir):
        PROJECT_ROOT = release_dir

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

from app import app as application
