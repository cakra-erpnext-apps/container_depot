"""Move the manhour_rate custom field from Price List to Item Price.

manhour_rate now lives on each Item Price row (per item + price list) instead of
once per Price List, so a principal's rate card can carry a distinct labour rate
per service. Old Price List values are dropped, not migrated.

- delete the obsolete "Price List-manhour_rate" Custom Field (drops the column)
- (re)create the new "Item Price-manhour_rate" Custom Field via setup_custom_fields

Idempotent: safe to re-run and a no-op on fresh installs (where the field is
created directly on Item Price).
"""

import frappe

from container_depot.install import setup_custom_fields


def execute():
	if frappe.db.exists("Custom Field", "Price List-manhour_rate"):
		frappe.delete_doc("Custom Field", "Price List-manhour_rate", ignore_permissions=True)

	# delete_doc on a Custom Field does not drop the DB column; drop it explicitly
	# so manhour_rate is gone from tabPrice List too (old values discarded).
	frappe.db.sql_ddl("ALTER TABLE `tabPrice List` DROP COLUMN IF EXISTS `manhour_rate`")

	# Creates the Item Price-manhour_rate custom field (idempotent).
	setup_custom_fields()
	frappe.db.commit()
