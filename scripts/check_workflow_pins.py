#!/usr/bin/env python3
"""Require immutable SHA pins for every third-party GitHub Action reference."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
text = WORKFLOW.read_text(encoding="utf-8")
refs = re.findall(r"^\s*uses:\s*([^\s#]+)", text, flags=re.MULTILINE)
if not refs:
    print("WORKFLOW PIN CHECK FAILED: no action references found", file=sys.stderr)
    raise SystemExit(1)

problems = []
for ref in refs:
    if ref.startswith("./"):
        continue
    match = re.fullmatch(r"[^@]+@([0-9a-f]{40})", ref)
    if not match:
        problems.append(ref)

if problems:
    print("WORKFLOW PIN CHECK FAILED: actions must use full 40-character commit SHAs:", file=sys.stderr)
    for ref in problems:
        print(f"- {ref}", file=sys.stderr)
    raise SystemExit(1)

print(f"Workflow action pin audit: PASS ({len(refs)} immutable action references)")
