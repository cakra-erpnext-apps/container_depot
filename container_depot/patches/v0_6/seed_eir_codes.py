"""PRD v0.2 §1 — seed the official OAK EIR Damage / Repair code masters.

Codes extracted verbatim from ``Eir_new_Rev_3.xlsx`` (the PT OASIS ANUGERAH KASIH
EIR template):

* Damage codes 01–29 + ``v`` (Acceptable) describe the *condition* of a part.
* Repair codes 30–54 + ``X`` (No Action) describe the *repair action*.

Note: the legacy Inspection Damage Entry.damage_type values (Gasket, Valve, Frame, …) were
*components*, not damage codes — those are moved to the new ``component`` field
by ``migrate_damage_type_to_component``. Idempotent: existing codes are skipped.
"""

from __future__ import annotations

import frappe

# (code, description) — order follows the workbook.
DAMAGE_CODES = [
	("01", "Gouged"),
	("02", "Saturated"),
	("03", "Out of Calibration"),
	("04", "Unserviceable"),
	("05", "Megohm Failure"),
	("06", "Modify"),
	("08", "Contaminated"),
	("09", "Bad Maintenance"),
	("10", "Hit Overhead"),
	("11", "Dented"),
	("12", "Broken"),
	("13", "Holed / Cut"),
	("14", "Dented & Holed"),
	("15", "Missing"),
	("16", "Loose"),
	("17", "Rusted"),
	("18", "Foreign Mark"),
	("19", "Cracked"),
	("20", "Out of ISO"),
	("21", "Foreign Fitting"),
	("22", "Test"),
	("23", "Waste Material"),
	("24", "Improper Repair - Old"),
	("25", "Improper Repair - New"),
	("26", "Manufacturers Defect"),
	("27", "Seized"),
	("28", "ARD (Wear & Tear)"),
	("29", "Pitted"),
	("v", "Acceptable"),
]

REPAIR_CODES = [
	("30", "Straighten"),
	("31", "Insert"),
	("32", "Section"),
	("33", "Renew"),
	("34", "Weld"),
	("35", "Straighten & Weld"),
	("36", "Remove"),
	("38", "Wash Out"),
	("39", "Steam Clean"),
	("40", "Blast & Paint"),
	("41", "Wire Brush & Paint"),
	("42", "Special Repairs"),
	("43", "Seal"),
	("44", "Resecure"),
	("45", "Free & Ease"),
	("46", "Patching"),
	("47", "GRP Infil"),
	("48", "Deodorise"),
	("49", "Polish Clean"),
	("50", "Grind Smooth"),
	("51", "Dry out"),
	("52", "Test / Calibrate"),
	("53", "Dismantle & Clean"),
	("54", "Passive"),
	("X", "No Action"),
]


def execute():
	for code, description in DAMAGE_CODES:
		if not frappe.db.exists("Inspection Damage Code", code):
			frappe.get_doc({
				"doctype": "Inspection Damage Code",
				"code": code,
				"category": "Damage",
				"description": description,
				"is_active": 1,
			}).insert(ignore_permissions=True)

	for code, description in REPAIR_CODES:
		if not frappe.db.exists("Inspection Repair Code", code):
			frappe.get_doc({
				"doctype": "Inspection Repair Code",
				"code": code,
				"category": "Repair",
				"description": description,
				"is_active": 1,
			}).insert(ignore_permissions=True)

	frappe.db.commit()
	print(
		f"[container_depot] seed_eir_codes: ensured {len(DAMAGE_CODES)} damage code(s), "
		f"{len(REPAIR_CODES)} repair code(s)."
	)
