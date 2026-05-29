"""Scheduled jobs registered via :mod:`container_depot.hooks.scheduler_events`."""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime


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
