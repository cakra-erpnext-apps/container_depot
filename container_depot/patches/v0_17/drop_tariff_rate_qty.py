"""Drop the removed `qty` column from Tariff Rate.

The Price List lines no longer carry a per-line qty (billing quantity comes from
the booking / storage days, never the rate card). sync_all never drops columns
for removed fields, so drop it explicitly. Runs in [pre_model_sync] so the column
is gone before the schema is reconciled. Idempotent.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Tariff Rate"):
		return
	frappe.db.sql_ddl("ALTER TABLE `tabTariff Rate` DROP COLUMN IF EXISTS `qty`")
	frappe.db.commit()
