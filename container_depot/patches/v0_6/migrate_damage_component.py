"""PRD v0.2 §1 — move legacy Inspection Damage Entry.damage_type values into ``component``.

The old ``damage_type`` Select held *components* (Gasket, Valve, Frame, Door,
Floor, Interior_Lining, Manlid, Hinges, Locking_Rod, Other) — not OAK damage
codes. After the v0.2 cutover ``damage_type`` is a Link to Inspection Damage Code (the
condition codes 01-29/v). So any legacy value that is not a real damage code is
moved into the new ``component`` field and ``damage_type`` is cleared.

Runs after ``seed_eir_codes`` (so the official codes already exist). Idempotent.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Inspection Damage Entry", "damage_type"):
		return
	if not frappe.db.has_column("Inspection Damage Entry", "component"):
		return

	valid_codes = set(frappe.get_all("Inspection Damage Code", pluck="name"))

	rows = frappe.db.sql(
		"""
		SELECT name, damage_type, component
		FROM `tabInspection Damage Entry`
		WHERE damage_type IS NOT NULL AND damage_type != ''
		""",
		as_dict=True,
	)
	moved = 0
	for r in rows:
		if r.damage_type in valid_codes:
			continue  # already a real damage code — leave it
		# Legacy component value sitting in damage_type: relocate it.
		component = r.component or r.damage_type.replace("_", " ")
		frappe.db.set_value(
			"Inspection Damage Entry",
			r.name,
			{"component": component, "damage_type": None},
			update_modified=False,
		)
		moved += 1

	if moved:
		frappe.db.commit()
	print(f"[container_depot] migrate_damage_component: relocated {moved} legacy value(s) to component.")
