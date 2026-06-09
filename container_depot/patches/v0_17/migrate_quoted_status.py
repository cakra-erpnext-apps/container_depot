"""Migrate Depot Contract data for the slimmed status set + required currency.

The status enum dropped "Quoted" (folded into "Negotiation") and added "Void".
The contract also gained a required `currency` field (the published Price List /
Item Prices inherit it). Backfill both on existing rows, non-destructively.

Runs in [post_model_sync] so the new field/enum exist. Raw SQL is used so this
does not fire the contract's on_update publish logic. Idempotent.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Depot Contract"):
		return

	# Retired status value -> Negotiation.
	frappe.db.sql("UPDATE `tabDepot Contract` SET status='Negotiation' WHERE status='Quoted'")

	# Backfill currency (now required) where missing, from the customer's default
	# currency, else the system default.
	default_currency = frappe.defaults.get_global_default("currency") or "IDR"
	rows = frappe.get_all(
		"Depot Contract",
		filters={"currency": ["in", [None, ""]]},
		fields=["name", "customer"],
	)
	for row in rows:
		cur = frappe.db.get_value("Customer", row.customer, "default_currency") or default_currency
		frappe.db.set_value("Depot Contract", row.name, "currency", cur, update_modified=False)

	frappe.db.commit()
