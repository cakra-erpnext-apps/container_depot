"""PRD v0.2 §3 — multi-depo: seed Depot master + backfill existing records.

Seeds the two known OAK depots (Surabaya, OAK Medan / KIM 11) and backfills the
new ``depot`` Link on every core operational entity. All pre-v0.2 data belongs
to the original Surabaya depot, so that is the backfill default.

Idempotent: re-running skips depots that already exist and only fills rows whose
``depot`` is still blank.
"""

from __future__ import annotations

import frappe

DEFAULT_DEPOT_CODE = "SUB"

# (depot_code, depot_name, city)
SEED_DEPOTS = [
	("SUB", "Surabaya", "Surabaya"),
	("KIM11", "OAK Medan (KIM 11)", "Medan"),
]

# Core entities that gained a ``depot`` Link in v0.2.
BACKFILL_DOCTYPES = [
	"Container",
	"Isotank Booking",
	"Gate Entry",
	"Inspection",
	"Cleaning Order",
	"Repair Order",
]


def execute():
	for code, name, city in SEED_DEPOTS:
		if not frappe.db.exists("Depot", code):
			frappe.get_doc({
				"doctype": "Depot",
				"depot_code": code,
				"depot_name": name,
				"city": city,
				"is_active": 1,
			}).insert(ignore_permissions=True)

	if not frappe.db.exists("Depot", DEFAULT_DEPOT_CODE):
		# Defensive: nothing to backfill onto.
		frappe.db.commit()
		return

	filled = 0
	for dt in BACKFILL_DOCTYPES:
		if "depot" not in [f.fieldname for f in frappe.get_meta(dt).fields]:
			continue
		rows = frappe.get_all(
			dt,
			filters={"depot": ("in", ["", None])},
			pluck="name",
		)
		for name in rows:
			frappe.db.set_value(dt, name, "depot", DEFAULT_DEPOT_CODE, update_modified=False)
		filled += len(rows)

	frappe.db.commit()
	print(f"[container_depot] seed_depots: ensured {len(SEED_DEPOTS)} depot(s); backfilled {filled} row(s) to {DEFAULT_DEPOT_CODE}.")
