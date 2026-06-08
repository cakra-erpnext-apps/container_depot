"""Rename the Isotank-prefixed doctypes (and their tables) to Container.

Runs in [pre_model_sync] so the DB rename happens *before* sync_all reads the
on-disk JSON (already named "Container ..."). If it ran post-sync, sync_all
would create fresh empty Container* tables and the rename would then collide.

Children are renamed before their parents so that frappe's
``update_parenttype_values`` (invoked during the parent rename) can rewrite the
child rows' ``parenttype`` via the parent's already-updated table-field options.
A defensive parenttype fixup follows in case anything was missed.

Idempotent: each rename is guarded by an existence check, so the patch is a
no-op on fresh installs (where these doctypes are created as Container* directly)
and on re-runs.
"""

import frappe

# (old, new) — children first, then parents.
RENAMES = [
	("Isotank Booking Item", "Container Booking Item"),
	("Isotank Booking", "Container Booking"),
	("Isotank Leasing History", "Container Leasing History"),
	("Isotank Leasing", "Container Leasing"),
]

# (child doctype, old parenttype, new parenttype)
PARENTTYPE_FIXUPS = [
	("Container Booking Item", "Isotank Booking", "Container Booking"),
	("Container Leasing History", "Isotank Leasing", "Container Leasing"),
]


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
		# rename touches link-field caches; reset between renames.
		frappe.flags.link_fields = {}

	for child, parent_old, parent_new in PARENTTYPE_FIXUPS:
		if frappe.db.table_exists(child):
			frappe.db.sql(
				f"UPDATE `tab{child}` SET parenttype=%s WHERE parenttype=%s",
				(parent_new, parent_old),
			)

	frappe.clear_cache()
