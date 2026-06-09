"""Drop the old service-based Tariff Rate rows ahead of the item-based schema.

Tariff Rate moves from service/cleaning_type/currency to item/uom/rate/
manhour_rate/qty. The legacy rows have no Item and are intentionally discarded
(rates now live in Item Price; contracts are re-entered against catalog Items).

Runs in [pre_model_sync] so the rows are gone BEFORE sync_all alters the table
(drops `service`/`cleaning_type`/`currency`, retypes `uom` to a Link, adds
`item`/`qty`), leaving a clean empty table for the schema change. Idempotent.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Tariff Rate"):
		return

	frappe.db.delete("Tariff Rate")

	# sync_all never drops columns for removed fields; drop the legacy service
	# columns explicitly so nothing service-based survives on the table.
	for col in ("service", "cleaning_type", "currency"):
		frappe.db.sql_ddl(f"ALTER TABLE `tabTariff Rate` DROP COLUMN IF EXISTS `{col}`")

	frappe.db.commit()
