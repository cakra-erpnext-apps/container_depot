#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("/home/frappe/frappe-bench/apps/crm")
OLD = "from frappe.desk.form.assign_to import _add as assign"
NEW = """try:\n\tfrom frappe.desk.form.assign_to import _add as assign\nexcept ImportError:\n\tfrom frappe.desk.form.assign_to import add as assign"""

if not ROOT.exists():
    print(f"CRM app not found: {ROOT}")
    raise SystemExit(0)

patched = 0
for path in ROOT.rglob("*.py"):
    text = path.read_text()
    if OLD in text:
        path.write_text(text.replace(OLD, NEW))
        print(f"patched {path}")
        patched += 1

print(f"crm assign_to compatibility patches: {patched}")
