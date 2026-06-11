"""Rename the EIR-prefixed doctypes (and the generic ``Damage Entry``) — and their
tables — to ``Inspection ...`` so every table that stores an Inspection's data lines
up under the "Inspection" doctype/menu.

    Damage Entry        -> Inspection Damage Entry   (child table)
    EIR Item Photo      -> Inspection Item Photo      (child table)
    EIR Checklist Item  -> Inspection Checklist Item  (master)
    EIR Damage Code     -> Inspection Damage Code     (master)
    EIR Repair Code     -> Inspection Repair Code     (master)

Runs in [pre_model_sync] so the DB rename happens BEFORE sync_all reads the on-disk
JSON (already named "Inspection ..."). Post-sync would create fresh empty tables and
the rename would then collide.

The parent (``Inspection``) is NOT renamed, so the child rows' ``parenttype`` stays
valid; only the child / master doctypes + their tables move. ``rename_doc`` rewrites
the dependent Link / Table field options and the data references; the master record
*names* (code "11"/"v", item_code "01"…) are unchanged, so stored Link values stay
valid. Idempotent: each rename is existence-guarded, so it is a no-op on fresh
installs (created as Inspection* directly from JSON) and on re-runs.

Repair Estimate Item (shared with Repair Order) and Inspection Photo (already
correctly named) are intentionally left untouched.
"""

import frappe

# children first, then masters (order is not load-bearing here — the parent
# Inspection is not renamed — but mirrors the v0_14 precedent).
RENAMES = [
	("Damage Entry", "Inspection Damage Entry"),
	("EIR Item Photo", "Inspection Item Photo"),
	("EIR Checklist Item", "Inspection Checklist Item"),
	("EIR Damage Code", "Inspection Damage Code"),
	("EIR Repair Code", "Inspection Repair Code"),
]


def execute():
	for old, new in RENAMES:
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
		# rename touches link-field caches; reset between renames.
		frappe.flags.link_fields = {}

	frappe.clear_cache()
