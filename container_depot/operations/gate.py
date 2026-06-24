"""Gate Entry history for the PWA "Riwayat Gate" feed.

Mirrors ``operations.eir``: deliberately free of ``@frappe.whitelist`` so the ``ess.gate``
endpoints add only auth + whitelisting. Lists Gate Entries (the gate-in / gate-out voucher
records) newest first and returns one record's full vehicle / order / EIR detail, depot-scoped
to the caller's branch.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from container_depot.operations.user_branch import assert_in_user_branch, get_user_depots

_LIST_FIELDS = [
	"name", "gate_entry_id", "container_no", "status", "booking_code", "depot",
	"truck_plate", "driver_name", "gate_in_timestamp", "gate_out_timestamp",
	"eir_reference", "inspection_status", "creation",
]


def list_gate_history(start=0, page_length=10, search=None) -> dict:
	"""Gate Entry records (gate-in/out vouchers), newest first, paginated + searchable,
	depot-scoped to the caller's branch."""
	filters = {}
	depots = get_user_depots()
	if depots is not None:
		filters["depot"] = ["in", depots or [""]]
	or_filters = None
	search = (search or "").strip()
	if search and search.lower() != "undefined":
		or_filters = {
			"container_no": ["like", f"%{search}%"],
			"gate_entry_id": ["like", f"%{search}%"],
			"booking_code": ["like", f"%{search}%"],
			"truck_plate": ["like", f"%{search}%"],
		}
	items = frappe.get_all(
		"Gate Entry", filters=filters, or_filters=or_filters,
		fields=_LIST_FIELDS, order_by="creation desc",
		limit_start=cint(start), limit_page_length=cint(page_length),
	)
	return {"items": items, "total": frappe.db.count("Gate Entry", filters)}


def get_gate_detail(name) -> dict:
	"""One Gate Entry's full detail (vehicle, order ref, EIR ref), branch-guarded."""
	if not name:
		frappe.throw(_("name is required."))
	doc = frappe.get_doc("Gate Entry", name)
	assert_in_user_branch(depot=doc.depot)
	return {
		"name": doc.name,
		"gate_entry_id": doc.gate_entry_id,
		"status": doc.status,
		"booking_code": doc.booking_code,
		"depot": doc.depot,
		"order_doctype": doc.order_doctype,
		"order_ref": doc.order_ref,
		"container_no": doc.container_no,
		"security_guard": doc.security_guard,
		"truck_plate": doc.truck_plate,
		"driver_name": doc.driver_name,
		"gate_in_timestamp": str(doc.gate_in_timestamp) if doc.gate_in_timestamp else None,
		"gate_out_timestamp": str(doc.gate_out_timestamp) if doc.gate_out_timestamp else None,
		"eir_reference": doc.eir_reference,
		"inspection_status": doc.inspection_status,
		"docstatus": doc.docstatus,
	}
