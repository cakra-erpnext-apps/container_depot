"""ESS PWA Yard / Depot Storage endpoints — thin ``@frappe.whitelist`` wrappers.

Per the integration rule (see ``ess/inspections.py``): endpoints here only add
authentication + whitelisting + GET/POST gating + the placement role guard; all
yard logic (recommendation, occupancy, audited placement) lives in
``container_depot.operations.yard`` so the same code backs the PWA and Desk.

Backs the "Depot Storage" feature where an Operator Kalmar views containers per
zone, gets an empty-zone recommendation by status, and records where a tank is
stacked.
"""

from __future__ import annotations

import frappe
from frappe import _

from container_depot.api import _require_authenticated_user
from container_depot.operations import yard

# Roles allowed to RECORD a placement. Reads stay open to any authenticated PWA
# user (and remain permission-aware on the underlying Container/Yard Zone rows).
YARD_OPERATOR_ROLES = {"Operator Kalmar", "Admin Ops", "Ops Supervisor", "System Manager"}


def _require_yard_operator() -> None:
	_require_authenticated_user()
	if set(frappe.get_roles(frappe.session.user)).isdisjoint(YARD_OPERATOR_ROLES):
		frappe.throw(_("You are not authorised to record yard placements."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def yard_overview(depot=None):
	"""GET /api/v1/ess/yard-overview — zone occupancy vs capacity + the depot list.

	The ``depots`` array drives the PWA's depot toggle; ``zones`` is the flat,
	occupancy-annotated list the page groups by depot/block.
	"""
	_require_authenticated_user()
	zones = yard.zone_occupancy(depot=depot)

	codes = list(dict.fromkeys(z["depot"] for z in zones if z["depot"]))
	names = (
		frappe.get_all("Depot", filters={"name": ["in", codes]}, fields=["name", "depot_name"])
		if codes
		else []
	)
	name_by_code = {d.name: d.depot_name for d in names}
	depots = [{"code": c, "name": name_by_code.get(c, c)} for c in codes]

	return {"success": True, "zones": zones, "depots": depots}


@frappe.whitelist(methods=["GET"])
def yard_zone_tanks(zone, search=None, start=0, page_length=50):
	"""GET /api/v1/ess/yard-zone-tanks — containers currently in one zone.

	Reuses the permission-aware tank list so depot scoping / DocPerms still apply.
	"""
	_require_authenticated_user()
	from container_depot.ess.inventory import get_tank_list

	return get_tank_list(yard_zone=zone, search=search, start=start, page_length=page_length)


@frappe.whitelist(methods=["GET"])
def yard_recommend(container_no):
	"""GET /api/v1/ess/yard-recommend — ranked zone suggestions for a container."""
	_require_authenticated_user()
	return {"success": True, **yard.recommend_zones(container_no)}


@frappe.whitelist(methods=["POST"])
def yard_place(container_no, zone, row=None, tier=None, bay=None):
	"""POST /api/v1/ess/yard-place — record a placement (audited Container Movement).

	Mutating + restricted to yard-operator roles.
	"""
	_require_yard_operator()
	return yard.place_container(
		container_no=container_no,
		zone=zone,
		row=row,
		tier=tier,
		bay=bay,
		moved_by=frappe.session.user,
	)
