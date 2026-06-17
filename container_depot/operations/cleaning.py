"""Core ISO Tank Cleanliness Statement logic for the web/checklist flow.

Mirrors ``operations/eir.py``: deliberately free of ``@frappe.whitelist`` so the
same functions back both the ESS PWA wrappers (``ess/cleaning.py``) and any Desk /
automation caller — the endpoint layer only adds auth + whitelisting.

The statement inspects a physical container, so the **Container is the key**: its
template fields (tank type, manufacture / last-test date, tare, MWG, capacity,
principal, previous cargo) come straight from the Container master. The surveyor
fills the 12 cleanliness checks + gas-free + seal numbers; submit (in the
controller) drives the Container and mints the gating certificate.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import today

from container_depot.operations.user_branch import assert_in_user_branch, get_user_branches

# Default boiler-plate the OAK statement prints unless the surveyor overrides it.
DEFAULT_REMARKS = "TANK ALREADY STEAM 100°C\nTANK ALREADY PASSED LEAK TEST 1 BAR"


def _guard_container_branch(container_name) -> None:
	"""Block cleaning-statement actions on a container outside the user's branch."""
	depot = frappe.db.get_value("Container", container_name, "depot")
	assert_in_user_branch(depot=depot)


def get_cleaning_masters() -> dict:
	"""Checklist taxonomy (grouped by section) + default remarks for the PWA form."""
	checklist = frappe.get_all(
		"Cleaning Checklist Item",
		filters={"is_active": 1},
		fields=["item_code", "section", "item_name", "sequence"],
		order_by="sequence asc",
	)
	return {
		"checklist": checklist,
		"default_remarks": DEFAULT_REMARKS,
	}


def _resolve_container(container=None, container_no=None) -> str:
	name = container or container_no
	if not name:
		frappe.throw(_("Provide a container number."))
	if not frappe.db.exists("Container", name):
		# container_no may differ from docname on legacy data — look it up.
		name = frappe.db.get_value("Container", {"container_no": name}) or name
	if not frappe.db.exists("Container", name):
		frappe.throw(_("Container {0} not found.").format(container or container_no))
	return name


def _latest_eir(container: str) -> str | None:
	"""The newest submitted EIR for the container (the statement's validity anchor)."""
	return frappe.db.get_value(
		"Inspection",
		{"container": container, "docstatus": 1, "inspection_type": ["in", ["EIR-In", "EIR-Out"]]},
		"name",
		order_by="creation desc",
	)


def _default_place_of_issue(user, depot) -> str | None:
	"""Branch default for ``place_of_issue`` — the user's first branch, else the depot."""
	branches = get_user_branches(user)
	if branches:
		return branches[0]
	return depot


def prefill(container=None, container_no=None, inspection=None) -> dict:
	"""Resolve the statement header from the Container master + auto fields.

	AUTO-FILL (from Container): tank_no, tank_type, date_of_manufacture, tare, mgw,
	capacity, client/principal, last_test_date, previous_cargo. AUTO: date_of_issue =
	today, place_of_issue = branch default, signed_by = session user. ``inspection`` is
	the source EIR (defaulted to the container's latest submitted EIR).
	"""
	name = _resolve_container(container, container_no)
	c = frappe.db.get_value(
		"Container", name,
		["name", "container_no", "container_type", "manufacture_date", "last_test_date",
		 "tare_weight", "max_gross_weight", "capacity", "principal", "last_cargo",
		 "depot", "seal_manhole", "seal_airline", "seal_bottom_outlet"],
		as_dict=True,
	)
	if not c:
		frappe.throw(_("Container {0} not found.").format(container or container_no))

	_guard_container_branch(c.name)

	user = frappe.session.user
	return {
		"container": c.name,
		"container_no": c.container_no,
		"tank_no": c.container_no,
		"tank_type": c.container_type,
		"date_of_manufacture": c.manufacture_date,
		"last_test_date": c.last_test_date,
		"tare": c.tare_weight,
		"mgw": c.max_gross_weight,
		"capacity": c.capacity,
		"client": c.principal,
		"previous_cargo": c.last_cargo,
		"depot": c.depot,
		# Seals prefilled from the container's last-known values (editable).
		"seal_manhole": c.seal_manhole,
		"seal_airline": c.seal_airline,
		"seal_bottom_outlet": c.seal_bottom_outlet,
		# AUTO header.
		"date_of_issue": today(),
		"place_of_issue": _default_place_of_issue(user, c.depot),
		"signed_by": user,
		"inspection": inspection or _latest_eir(c.name),
		"default_remarks": DEFAULT_REMARKS,
	}


def _coerce_list(value) -> list:
	if isinstance(value, str):
		value = json.loads(value) if value.strip() else []
	return value or []


def _as_bool(value) -> bool:
	if isinstance(value, str):
		return value.strip().lower() in ("1", "true", "yes")
	return bool(value)


def _build_checklist_rows(results) -> list:
	"""Map the surveyor's payload to Cleaning Statement Item rows for ALL active items.

	Every active checklist item is recorded (full statement). ``results`` is a flat
	``[{item_code, result, note}]`` payload; missing items default to result "Yes".
	"""
	items = frappe.get_all(
		"Cleaning Checklist Item",
		filters={"is_active": 1},
		fields=["item_code", "section", "item_name"],
		order_by="sequence asc",
	)
	by_code = {}
	for r in _coerce_list(results):
		code = (r.get("item_code") or "").strip()
		if code:
			by_code[code] = r
	rows = []
	for it in items:
		payload = by_code.get(it.item_code, {})
		result = (payload.get("result") or "").strip() or "Yes"
		if result not in ("Yes", "No"):
			frappe.throw(_("Checklist result must be Yes or No (item {0}).").format(it.item_code))
		rows.append({
			"checklist_item": it.item_code,
			"section": it.section,
			"item_name": it.item_name,
			"result": result,
			"note": (payload.get("note") or "").strip() or None,
		})
	return rows


def create_cleaning_statement(
	container=None,
	inspection=None,
	date_of_issue=None,
	place_of_issue=None,
	gas_free=None,
	o2_percent=None,
	lel_percent=None,
	seal_manhole=None,
	seal_airline=None,
	seal_bottom_outlet=None,
	remarks=None,
	signature=None,
	results=None,
	submit=False,
) -> dict:
	"""Build (and optionally submit) a Cleaning Statement from the PWA payload.

	The header auto-fields (tank spec, principal, previous cargo, depot) are resolved
	server-side from the Container so the client only sends the surveyor's input. When
	``submit`` is true the statement is submitted and its ``on_submit`` moves the
	container toward Available + mints the no-expiry Cleaning Certificate. Permissions
	are NOT bypassed — Frappe enforces Cleaning Statement create/submit on the caller.
	"""
	if not container:
		frappe.throw(_("container is required."))
	name = _resolve_container(container)
	_guard_container_branch(name)

	pf = prefill(container=name, inspection=inspection)

	doc = frappe.new_doc("Cleaning Statement")
	doc.container = name
	doc.container_no = pf["container_no"]
	doc.inspection = inspection or pf.get("inspection")
	doc.depot = pf.get("depot")
	doc.date_of_issue = date_of_issue or pf["date_of_issue"]
	doc.place_of_issue = place_of_issue or pf.get("place_of_issue")
	doc.signed_by = frappe.session.user
	# Tank spec snapshot (also covered by fetch_from for Desk entry).
	doc.tank_type = pf.get("tank_type")
	doc.date_of_manufacture = pf.get("date_of_manufacture")
	doc.last_test_date = pf.get("last_test_date")
	doc.tare = pf.get("tare")
	doc.mgw = pf.get("mgw")
	doc.capacity = pf.get("capacity")
	doc.client = pf.get("client")
	doc.previous_cargo = pf.get("previous_cargo")
	# Surveyor input.
	doc.gas_free = gas_free
	doc.o2_percent = o2_percent
	doc.lel_percent = lel_percent
	doc.seal_manhole = seal_manhole
	doc.seal_airline = seal_airline
	doc.seal_bottom_outlet = seal_bottom_outlet
	doc.remarks = remarks if remarks is not None else DEFAULT_REMARKS
	doc.surveyor_signature = signature
	doc.set("checklist", _build_checklist_rows(results))

	doc.insert()  # NOT ignore_permissions — let Frappe enforce Cleaning Statement create.
	if _as_bool(submit):
		doc.submit()  # on_submit drives the container + mints the certificate.

	return {
		"success": True,
		"name": doc.name,
		"statement_id": doc.statement_id,
		"docstatus": doc.docstatus,
		"cleaning_certificate": doc.get("cleaning_certificate"),
	}


def list_my_statements(user=None, search=None, start=0, page_length=10, docstatus=None) -> dict:
	"""Paginated list of the caller's own Cleaning Statements (newest first)."""
	from frappe.utils import cint

	user = user or frappe.session.user
	filters = {"owner": user}
	if docstatus is not None and str(docstatus) != "":
		filters["docstatus"] = cint(docstatus)
	or_filters = None
	if search:
		or_filters = {"container_no": ["like", f"%{search}%"], "statement_id": ["like", f"%{search}%"]}
	items = frappe.get_all(
		"Cleaning Statement",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "statement_id", "container", "container_no", "date_of_issue", "docstatus"],
		order_by="creation desc",
		start=cint(start),
		page_length=cint(page_length),
	)
	total = frappe.db.count("Cleaning Statement", filters)
	return {"items": items, "total": total, "start": cint(start), "page_length": cint(page_length)}
