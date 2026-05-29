"""Daily Operations Report — single-page snapshot of the depot's current day.

Sections (one row each, ``metric`` column carries the label):

- Containers by status
- Bookings by status (today)
- Pending Orders (Bongkar / Muat)
- Booking Codes expiring in the next 24h
- Overdue Cleaning Certificates (valid_until < today)
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, today


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	data = []

	data.extend(_containers_by_status())
	data.append(_separator("Bookings"))
	data.extend(_bookings_today())
	data.append(_separator("Orders"))
	data.extend(_pending_orders())
	data.append(_separator("Booking Codes"))
	data.extend(_codes_expiring_soon())
	data.append(_separator("Cleaning Certificates"))
	data.extend(_overdue_certs())

	return columns, data


def _columns():
	return [
		{"fieldname": "section", "label": "Section", "fieldtype": "Data", "width": 160},
		{"fieldname": "metric", "label": "Metric", "fieldtype": "Data", "width": 280},
		{"fieldname": "count", "label": "Count", "fieldtype": "Int", "width": 100},
	]


def _separator(section: str):
	return {"section": "", "metric": f"── {section} ──", "count": None}


def _containers_by_status():
	rows = frappe.db.sql(
		"""
		SELECT status, COUNT(*) AS c
		FROM `tabContainer`
		GROUP BY status
		ORDER BY c DESC
		""",
		as_dict=True,
	)
	return [{"section": "Containers", "metric": r["status"] or "(blank)", "count": r["c"]} for r in rows]


def _bookings_today():
	rows = frappe.db.sql(
		"""
		SELECT booking_status, COUNT(*) AS c
		FROM `tabIsotank Booking`
		WHERE DATE(creation) = %s
		GROUP BY booking_status
		ORDER BY c DESC
		""",
		(today(),),
		as_dict=True,
	)
	return [{"section": "Bookings (today)", "metric": r["booking_status"], "count": r["c"]} for r in rows]


def _pending_orders():
	out = []
	for dt in ("Order Bongkar", "Order Muat"):
		rows = frappe.db.sql(
			f"""
			SELECT order_status, COUNT(*) AS c
			FROM `tab{dt}`
			WHERE order_status NOT IN ('Completed', 'Hold')
			GROUP BY order_status
			""",
			as_dict=True,
		)
		out.extend(
			{"section": dt, "metric": r["order_status"], "count": r["c"]} for r in rows
		)
	return out


def _codes_expiring_soon():
	end = add_days(today(), 1)
	rows = frappe.db.sql(
		"""
		SELECT direction, COUNT(*) AS c
		FROM `tabBooking Code`
		WHERE state = 'Active' AND expires_at <= %s
		GROUP BY direction
		""",
		(end,),
		as_dict=True,
	)
	return [
		{"section": "Codes expiring ≤24h", "metric": r["direction"], "count": r["c"]}
		for r in rows
	]


def _overdue_certs():
	count = frappe.db.count(
		"Cleaning Certificate",
		{"docstatus": 1, "valid_until": ("<", today())},
	)
	return [{"section": "Cleaning Certificates", "metric": "Expired", "count": count}]
