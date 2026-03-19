"""
Demo reset — restores main.py and keyword.py to pre-demo state.
Run this before each demo run to start clean.

Usage:
    python demo/reset.py
"""

import shutil
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    ("demo/main.py.snapshot",         "app/main.py"),
    ("demo/keyword.py.snapshot",       "app/rules/keyword.py"),
]

for src, dst in FILES:
    src_path = os.path.join(ROOT, src)
    dst_path = os.path.join(ROOT, dst)
    shutil.copy(src_path, dst_path)
    print(f"  reset: {dst}")

print("\nReady. Files restored to pre-demo state.")
print("Run demo/verify_before.py to confirm baseline, then start agents.")
