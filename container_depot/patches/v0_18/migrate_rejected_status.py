"""Fold the retired "Rejected" contract status into "Void".

The status set is now Draft / Negotiation / Active / Expired / Void, driven by
workflow buttons. "Rejected" (a declined quote) collapses into "Void" (the single
cancel / terminate state). Raw SQL so it does not fire the contract's transition
guard or publish logic. Idempotent.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Depot Contract"):
		return
	frappe.db.sql("UPDATE `tabDepot Contract` SET status='Void' WHERE status='Rejected'")
	frappe.db.commit()
