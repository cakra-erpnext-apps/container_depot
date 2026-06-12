"""Backfill the new Order Bongkar / Order Muat `branch` from their Container Booking.

`branch` was just added to the order doctypes (carried from the booking) so per-branch
User Permissions can scope orders. Existing bons have it empty — fill it via a direct
join so old orders filter correctly too. Value-only writes; safe on submitted docs.
Idempotent: only touches rows whose branch is still empty.
"""

import frappe


def execute():
	for dt in ("Order Bongkar", "Order Muat"):
		if not frappe.db.has_column(dt, "branch"):
			continue
		frappe.db.sql(
			"""
			UPDATE `tab{dt}` o
			INNER JOIN `tabContainer Booking` b ON b.name = o.booking
			SET o.branch = b.branch
			WHERE COALESCE(o.branch, '') = '' AND COALESCE(b.branch, '') != ''
			""".format(dt=dt)
		)
	frappe.db.commit()
