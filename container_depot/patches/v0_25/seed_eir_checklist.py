"""Seed the 50-row OAK EIR checklist taxonomy (Inspection Checklist Item master).

Rows verbatim from ``Eir_new_Rev_3.xlsx`` (10 areas, 50 items). ``sequence`` 1-50
is the canonical identity; ``item_code`` is the zero-padded sequence (``"01"``-
``"50"``); ``printed_no`` keeps the workbook's printed number as-is — duplicates
at printed 32 (Foot Valve / Ball-Butterfly) and 46 (Drain Hose / Sticker FOO) are
preserved on purpose.

Idempotent: existing items (by item_code) are skipped, so re-running is a no-op.
Mirrors the pattern of ``patches/v0_6/seed_eir_codes.py``.
"""

from __future__ import annotations

import frappe

# (sequence, printed_no, area, item_name) — order follows the workbook.
CHECKLIST = [
	(1, "1", "Frame", "Underside"),
	(2, "2", "Frame", "Left Side"),
	(3, "3", "Frame", "Front"),
	(4, "4", "Frame", "Right Side"),
	(5, "5", "Frame", "Rear"),
	(6, "6", "Frame", "Top"),
	(7, "7", "Frame", "Walkway"),
	(8, "8", "Frame", "Ladder"),
	(9, "9", "Shell", "Syphon Tube"),
	(10, "10", "Shell", "Surface Condition"),
	(11, "11", "Shell", "Shell Damage"),
	(12, "12", "Cladding", "Underside"),
	(13, "13", "Cladding", "Left Side"),
	(14, "14", "Cladding", "Front"),
	(15, "15", "Cladding", "Right Side"),
	(16, "16", "Cladding", "Rear"),
	(17, "17", "Cladding", "Top"),
	(18, "18", "Cladding", "Decals"),
	(19, "19", "Cladding", "Logo"),
	(20, "20", "Safety Valves", "Flame Trap"),
	(21, "21", "Safety Valves", "PV Valves"),
	(22, "22", "Safety Valves", "Bursting Disc / Gauge"),
	(23, "23", "Manway", "Swingbolts"),
	(24, "24", "Manway", "Manlid"),
	(25, "25", "Manway", "Customs Seal"),
	(26, "26", "Top Discharge", "Airline Cap / Seal"),
	(27, "27", "Top Discharge", "Top Valve"),
	(28, "28", "Top Discharge", "Airline Valve / Gauge"),
	(29, "29", "Top Discharge", "Blank"),
	(30, "30", "Top Discharge", "Top Compartment"),
	(31, "31", "Top Discharge", "Syphon Tube"),
	(32, "32", "Bottom Discharge", "Foot Valve"),
	(33, "32", "Bottom Discharge", "Ball / Butterfly Valve"),
	(34, "33", "Bottom Discharge", "Bottom Compartment"),
	(35, "34", "Bottom Discharge", "Outlet Cap / Blank"),
	(36, "35", "Bottom Discharge", "Remote Trip IM101"),
	(37, "36", "Heating", "Steam Tube / Cap"),
	(38, "37", "Heating", "Thermometer"),
	(39, "38", "Heating", "Electric"),
	(40, "39", "Heating", "Drain Valve"),
	(41, "40", "Heating", "Electric / Cable / Plug"),
	(42, "41", "Dipstick", "Dipstick"),
	(43, "42", "Dipstick", "Calibration Chart"),
	(44, "43", "Miscellaneous", "Data Plate"),
	(45, "44", "Miscellaneous", "Document Holder"),
	(46, "45", "Miscellaneous", "Compartments"),
	(47, "46", "Miscellaneous", "Drain Hose"),
	(48, "47", "Miscellaneous", "Sticker"),
	(49, "48", "Miscellaneous", "Grounding Plate"),
	(50, "46", "Miscellaneous", "Sticker FOO"),
]


def execute():
	for seq, printed_no, area, item_name in CHECKLIST:
		item_code = f"{seq:02d}"
		if frappe.db.exists("Inspection Checklist Item", item_code):
			continue
		frappe.get_doc({
			"doctype": "Inspection Checklist Item",
			"item_code": item_code,
			"printed_no": printed_no,
			"area": area,
			"item_name": item_name,
			"sequence": seq,
			"is_active": 1,
		}).insert(ignore_permissions=True)

	frappe.db.commit()
	print(f"[container_depot] seed_eir_checklist: ensured {len(CHECKLIST)} checklist item(s).")
