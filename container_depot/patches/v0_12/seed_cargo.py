"""Seed the Cargo master from the 2026 cargo list.

Data source: container_depot/data/cargo_list.json, generated from the
"List Cargo 2026" reference (Non-Stolt Standard/Difficult + Stolt Class A/B/C),
plus a synthetic "Empty Clean" entry for tanks that arrive empty.

Idempotent: existing cargo (matched by name) are left untouched.
"""

from __future__ import annotations

import json

import frappe


def execute():
	path = frappe.get_app_path("container_depot", "data", "cargo_list.json")
	with open(path, encoding="utf-8") as fh:
		rows = json.load(fh)

	seeded = 0
	for row in rows:
		name = (row.get("cargo_name") or "").strip()
		if not name or frappe.db.exists("Cargo", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Cargo",
				"cargo_name": name,
				"non_stolt_class": row.get("non_stolt_class") or None,
				"stolt_class": row.get("stolt_class") or None,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		seeded += 1

	frappe.db.commit()
	print(f"[container_depot] seed_cargo: ensured {seeded} cargo (of {len(rows)} in list).")
