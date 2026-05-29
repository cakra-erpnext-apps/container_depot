"""Scheduled jobs registered via :mod:`container_depot.hooks.scheduler_events`."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, now_datetime


SST_STALE_AFTER_MINUTES = 15


def expire_booking_codes() -> int:
	"""Flip Active Booking Codes whose ``expires_at`` is in the past to Expired.

	Runs hourly. Returns the count of rows transitioned (useful for tests).
	"""
	stale = frappe.get_all(
		"Booking Code",
		filters={"state": "Active", "expires_at": ("<", now_datetime())},
		fields=["name"],
		limit_page_length=0,
	)
	for row in stale:
		frappe.db.set_value(
			"Booking Code", row.name, "state", "Expired", update_modified=False
		)
	if stale:
		frappe.db.commit()
	return len(stale)


def mark_stale_sst_heartbeats() -> int:
	"""Flag SST terminals that have not heartbeated within the threshold.

	Runs every 5 minutes. Side-effects:
	- Sets ``printer_status='Stale'`` (if currently OK/Warning).
	- Opens one ToDo per stale terminal, addressed to anyone holding the
	  Ops Supervisor role.

	Returns the count of newly-stale terminals.
	"""
	threshold = add_to_date(now_datetime(), minutes=-SST_STALE_AFTER_MINUTES)
	rows = frappe.get_all(
		"Self Service Terminal",
		filters={"last_heartbeat": ("<", threshold), "printer_status": ("in", ["OK", "Warning"])},
		fields=["name", "terminal_id", "gate_location"],
	)
	if not rows:
		return 0

	supervisors = frappe.get_all(
		"Has Role",
		filters={"role": "Ops Supervisor", "parenttype": "User"},
		fields=["parent"],
		pluck="parent",
	)
	for row in rows:
		frappe.db.set_value(
			"Self Service Terminal", row.name, "printer_status", "Stale", update_modified=False
		)
		# Skip duplicate ToDo (one open per terminal).
		for user in supervisors:
			already = frappe.db.exists(
				"ToDo",
				{
					"reference_type": "Self Service Terminal",
					"reference_name": row.name,
					"allocated_to": user,
					"status": "Open",
				},
			)
			if already:
				continue
			frappe.get_doc({
				"doctype": "ToDo",
				"description": f"SST {row.terminal_id} ({row.gate_location or '-'}) has not heartbeated in {SST_STALE_AFTER_MINUTES}+ minutes.",
				"reference_type": "Self Service Terminal",
				"reference_name": row.name,
				"allocated_to": user,
				"priority": "High",
				"status": "Open",
			}).insert(ignore_permissions=True)
	frappe.db.commit()
	return len(rows)
