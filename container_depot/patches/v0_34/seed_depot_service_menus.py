"""Seed the default Depot Service Menus (Booking / Cleaning / Maintenance).

A menu is a named filter over the Item Groups already seeded by
patches.v0_11.seed_item_groups. We map each menu to its groups so item pickers
and the contract can filter by menu with ~zero per-item setup. Idempotent:
creates a menu only if absent, and only adds group rows that don't exist yet, so
hand-edits in Desk are preserved on re-run.
"""

from __future__ import annotations

import frappe

# Menu -> the Item Groups whose items belong to it. Only groups that exist are
# added (the list is defensive against renamed / missing groups).
MENU_GROUPS = {
	"Booking": [
		"Standard Depot Handling Charge",
		"Testing Charges",
		"Survey Fee",
	],
	"Cleaning": [
		"Cleaning Cost",
		"Exterior Cleaning Fee",
		"Interior Shell - Special Requirement",
	],
	"Maintenance": [
		"Repair & Spare Parts",
	],
}

SEQUENCE = {"Booking": 10, "Cleaning": 20, "Maintenance": 30}


def execute():
	for menu_name, groups in MENU_GROUPS.items():
		valid_groups = [g for g in groups if frappe.db.exists("Item Group", g)]

		if not frappe.db.exists("Depot Service Menu", menu_name):
			doc = frappe.new_doc("Depot Service Menu")
			doc.menu_name = menu_name
			doc.is_active = 1
			doc.sequence = SEQUENCE.get(menu_name, 0)
			for g in valid_groups:
				doc.append("item_groups", {"item_group": g})
			doc.insert(ignore_permissions=True)
			continue

		# Already exists — only add missing group rows (preserve hand edits).
		doc = frappe.get_doc("Depot Service Menu", menu_name)
		have = {row.item_group for row in (doc.get("item_groups") or [])}
		added = False
		for g in valid_groups:
			if g not in have:
				doc.append("item_groups", {"item_group": g})
				added = True
		if added:
			doc.save(ignore_permissions=True)

	frappe.db.commit()
	print(
		f"[container_depot] seed_depot_service_menus: ensured {len(MENU_GROUPS)} service menu(s)."
	)
