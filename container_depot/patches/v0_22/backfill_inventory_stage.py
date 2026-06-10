"""Backfill Container.inventory_stage from the raw status.

The new derived ``inventory_stage`` (Container Inventory monitoring) is kept in
step by ``Container.before_save``, but existing rows never re-save on migrate —
so map every current status onto its stage once here. Runs post_model_sync
(the column must exist). Idempotent — re-running just rewrites the same values.
"""

import frappe

from container_depot.state_machine import STAGE_BY_STATUS


def execute():
	if not frappe.db.has_column("Container", "inventory_stage"):
		return
	for status, stage in STAGE_BY_STATUS.items():
		frappe.db.sql(
			"UPDATE `tabContainer` SET `inventory_stage`=%s WHERE `status`=%s",
			(stage, status),
		)
	frappe.db.commit()
