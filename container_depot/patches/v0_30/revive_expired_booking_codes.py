"""Revive Booking Codes that were auto-expired by the (now removed) time-based
expiry.

Booking Codes no longer expire (the 72h TTL, the hourly ``expire_booking_codes``
task and all "code has expired" gate/bon blocks were removed). The ``Expired``
state was only ever set by that automatic time-based job — a deliberate kill uses
``Cancelled``/``Void`` — so any remaining ``Expired`` code that was never consumed
is safe to put back to ``Active`` so it can be issued again.

Idempotent: re-running flips nothing once no ``Expired`` codes remain.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Booking Code"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabBooking Code`
		SET state = 'Active'
		WHERE state = 'Expired'
		"""
	)
