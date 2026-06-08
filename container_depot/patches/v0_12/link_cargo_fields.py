"""Backfill the cargo fields after they were converted from Data to Link(Cargo).

For each doctype/field that now links to Cargo:
  * values that match an existing Cargo (case/space-insensitive) are normalised
    to the canonical Cargo name so the Link resolves;
  * values with no match get a Cargo record auto-created (no classification,
    is_active=1) so no Link is left dangling -- these are logged for review.

Runs after v0_12.seed_cargo (the master must exist first). Idempotent.
"""

from __future__ import annotations

import frappe

# (doctype, fieldname) pairs converted to Link -> Cargo
TARGETS = [
	("Container", "last_cargo"),
	("Cleaning Order", "last_cargo"),
	("Cleaning Certificate", "prior_cargo"),
	("Inspection", "last_cargo"),
	("Survey Request", "last_cargo"),
]


def _norm(s: str) -> str:
	return " ".join((s or "").split()).lower()


def execute():
	# canonical lookup: normalised name -> actual Cargo name
	cargo_by_norm = {_norm(n): n for n in frappe.get_all("Cargo", pluck="name")}

	normalised = 0
	created = []

	for doctype, field in TARGETS:
		if not frappe.db.exists("DocType", doctype) or not frappe.db.has_column(doctype, field):
			continue
		values = frappe.db.sql(
			f"SELECT DISTINCT `{field}` AS v FROM `tab{doctype}` "
			f"WHERE `{field}` IS NOT NULL AND `{field}` != ''",
			as_dict=True,
		)
		for row in values:
			val = row.v
			canonical = cargo_by_norm.get(_norm(val))
			if not canonical:
				# auto-create so the Link is not broken
				doc = frappe.get_doc(
					{"doctype": "Cargo", "cargo_name": val.strip(), "is_active": 1}
				).insert(ignore_permissions=True)
				canonical = doc.name
				cargo_by_norm[_norm(canonical)] = canonical
				created.append(canonical)
			if canonical != val:
				frappe.db.sql(
					f"UPDATE `tab{doctype}` SET `{field}` = %s WHERE `{field}` = %s",
					(canonical, val),
				)
				normalised += 1

	frappe.db.commit()
	print(
		f"[container_depot] link_cargo_fields: normalised {normalised} value(s); "
		f"auto-created {len(created)} cargo: {created}"
	)
