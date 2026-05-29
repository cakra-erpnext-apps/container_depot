"""Container.principal: Data -> Link Customer.

Runs after the doctype JSON has been synced (so the column type is already
Link), but the column still holds whatever text was there before. For each
distinct legacy value we:

1. Leave intact any value that already matches a Customer ``name``.
2. Translate values matching an existing Customer's ``customer_name`` to the
   Customer's ``name``.
3. Create a Customer for any remaining text (so no Container is orphaned),
   logging what we did to the migration log.

Idempotent: re-running finds everything already resolved and exits clean.
"""

from __future__ import annotations

import frappe


def execute():
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT principal
		FROM `tabContainer`
		WHERE principal IS NOT NULL AND principal != ''
		""",
		as_dict=False,
	)
	legacy_values = [r[0] for r in rows]
	if not legacy_values:
		print("[container_depot] Container.principal migration: no legacy values; nothing to do.")
		return

	created = []
	mapped = {}
	for value in legacy_values:
		v = (value or "").strip()
		if not v:
			continue
		# already a Customer name
		if frappe.db.exists("Customer", v):
			mapped[v] = v
			continue
		# matches a Customer's customer_name
		hit = frappe.db.get_value("Customer", {"customer_name": v}, "name")
		if hit:
			mapped[v] = hit
			continue
		# create a Customer for orphan text
		try:
			cust = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": v,
				"customer_type": "Company",
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups",
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
			}).insert(ignore_permissions=True)
			mapped[v] = cust.name
			created.append(cust.name)
		except Exception as exc:
			print(f"[container_depot] Could not auto-create Customer for {v!r}: {exc}")

	# Re-point the columns
	for legacy, resolved in mapped.items():
		if legacy != resolved:
			frappe.db.sql(
				"UPDATE `tabContainer` SET principal=%s WHERE principal=%s",
				(resolved, legacy),
			)

	frappe.db.commit()
	print(
		f"[container_depot] Container.principal migration: mapped {len(mapped)} value(s); "
		f"created {len(created)} Customer(s): {created}"
	)
