"""Retire the Cleaning Statement doctypes: their fields (EIR ref, cleanliness
checklist, gas free, seals, signature, certificate) now live directly on the
Cleaning Order — EIR -> Cleaning Order -> Cleaning Certificate. Runs pre-model-sync
so the orphan doctypes are gone before the schema re-syncs.

Idempotent: each delete is guarded by an existence check. Any submitted Cleaning
Statement rows are force-removed (the data was only ever the cleanliness detail,
which the Cleaning Order now carries). Cleaning Certificates already minted are
left untouched — they remain valid TANK OUT gating tokens.
"""

from __future__ import annotations

import frappe

_PRINT_FORMATS = ["Cleaning Statement Format"]
_DOCTYPES = ["Cleaning Statement", "Cleaning Statement Item"]


def execute():
	for pf in _PRINT_FORMATS:
		if frappe.db.exists("Print Format", pf):
			frappe.delete_doc("Print Format", pf, force=True, ignore_permissions=True)

	for dt in _DOCTYPES:
		if frappe.db.exists("DocType", dt):
			# Drop any rows first (force past docstatus), then the DocType meta.
			try:
				frappe.db.delete(dt)
			except Exception:
				pass
			frappe.delete_doc("DocType", dt, force=True, ignore_missing=True, ignore_permissions=True)
		# delete_doc does NOT drop the physical table while in_migrate; drop it explicitly
		# so no orphan `tab<DocType>` table is left behind.
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{dt}`")

	frappe.db.commit()
	print("[container_depot] drop_cleaning_statement: Cleaning Statement doctypes retired.")
