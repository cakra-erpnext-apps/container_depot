"""Seed the Yard Placement Rule master (Container status -> allowed Yard Zone
categories) from the canonical defaults in ``operations.yard.STATUS_TO_CATEGORY``.

Each status gets one rule whose ``allowed_categories`` child table lists the yard
categories it may sit in (the first is the recommended target). Once seeded the
mapping is user-editable in Desk and a status may list MULTIPLE categories;
``operations.yard`` reads the master and falls back to these defaults.

Idempotent: a rule is only created if missing, and its category list is only
populated when empty — preserving any user edits (and migrating an earlier
single-``category`` value if this patch ran before the multi-category rework).
"""

from __future__ import annotations

import frappe

from container_depot.operations.yard import STATUS_TO_CATEGORY


def _legacy_categories() -> dict:
	"""Single-``category`` values from before the child-table rework (column may
	still exist as an orphan); used to preserve edits on re-seed."""
	try:
		rows = frappe.db.sql("SELECT name, category FROM `tabYard Placement Rule`", as_dict=True)
		return {r.name: r.category for r in rows if r.get("category")}
	except Exception:
		return {}


def execute():
	legacy = _legacy_categories()
	for status, default_cat in STATUS_TO_CATEGORY.items():
		exists = frappe.db.exists("Yard Placement Rule", status)
		rule = frappe.get_doc("Yard Placement Rule", status) if exists else frappe.new_doc("Yard Placement Rule")
		rule.container_status = status
		if not rule.get("allowed_categories"):
			cat = legacy.get(status, default_cat)
			if cat:  # blank default = not placeable -> no categories
				rule.append("allowed_categories", {"category": cat})
		rule.flags.ignore_permissions = True
		rule.save() if exists else rule.insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"[container_depot] seed_yard_placement_rules: ensured {len(STATUS_TO_CATEGORY)} rule(s).")
