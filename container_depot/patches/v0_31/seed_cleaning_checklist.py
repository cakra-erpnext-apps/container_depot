"""Seed the 12-row OAK ISO Tank Cleanliness Statement checklist (Cleaning Checklist
Item master).

Rows verbatim from the OAK "ISO TANK CLEANLINESS STATEMENT" paper form, grouped into
three sections (Exterior, Interior, Valves & Fittings). ``sequence`` 1-12 is the
canonical order; ``item_code`` is the zero-padded sequence (``"01"``-``"12"``). The
gas-free reading is captured by dedicated header fields on the statement, not as a
checklist row.

Idempotent: existing items (by item_code) are skipped, so re-running is a no-op.
Mirrors the pattern of ``patches/v0_25/seed_eir_checklist.py``.
"""

from __future__ import annotations

import frappe

# (sequence, section, item_name) — order follows the OAK paper form.
CHECKLIST = [
	# EXTERIOR
	(1, "Exterior", "Exterior frame tank and walkways"),
	(2, "Exterior", "Manlid and valve compartment"),
	(3, "Exterior", "Serial numbers and statutory markings"),
	(4, "Exterior", "Cargo labels removed"),
	# INTERIOR
	(5, "Interior", "Entry made into tank by surveyor"),
	(6, "Interior", "Free from odour"),
	(7, "Interior", "Free from all cargo and contamination"),
	(8, "Interior", "Free from corrosion pitting"),
	(9, "Interior", "Dry"),
	# VALVES & FITTINGS
	(10, "Valves & Fittings", "Valves"),
	(11, "Valves & Fittings", "Manlid Seal"),
	(12, "Valves & Fittings", "Dip-Pipe"),
]


def execute():
	for seq, section, item_name in CHECKLIST:
		item_code = f"{seq:02d}"
		if frappe.db.exists("Cleaning Checklist Item", item_code):
			continue
		frappe.get_doc({
			"doctype": "Cleaning Checklist Item",
			"item_code": item_code,
			"section": section,
			"item_name": item_name,
			"sequence": seq,
			"is_active": 1,
		}).insert(ignore_permissions=True)

	frappe.db.commit()
	print(f"[container_depot] seed_cleaning_checklist: ensured {len(CHECKLIST)} checklist item(s).")
