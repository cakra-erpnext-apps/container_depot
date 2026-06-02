"""Drop the deprecated Voucher / Voucher Container DocTypes (Phase 5b-drop).

By the time this runs, ``v0_5.voucher_to_booking`` has already copied every
surviving Voucher into the Isotank Booking + Booking Code model (it runs
earlier in patches.txt). This patch physically removes the now-orphaned
DocTypes and their tables.

Idempotent: guarded by ``frappe.db.exists`` and ``DROP TABLE IF EXISTS``, so a
re-run on an already-dropped site is a no-op.
"""

from __future__ import annotations

import frappe


def execute():
	# Delete child first, then parent. delete_doc on the DocType also clears the
	# meta / docfield rows; force + ignore_permissions because this is a teardown.
	for doctype in ("Voucher Container", "Voucher"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
			print(f"[container_depot] Dropped DocType {doctype}.")

	# Belt-and-braces: drop the backing tables in case the DocType row was
	# already gone but the table lingered.
	frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabVoucher Container`")
	frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabVoucher`")
