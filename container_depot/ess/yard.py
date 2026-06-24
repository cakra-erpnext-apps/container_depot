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
from frappe.utils import cint

from container_depot.api import _require_authenticated_user
from container_depot.operations import yard
from container_depot.operations.user_branch import assert_in_user_branch, get_user_depots

# Roles allowed to RECORD a placement. Reads stay open to any authenticated PWA
# user (and remain permission-aware on the underlying Container/Yard Zone rows).
YARD_OPERATOR_ROLES = {"Operator Kalmar", "Admin Ops", "Ops Supervisor", "System Manager"}


def _require_yard_operator() -> None:
	_require_authenticated_user()
	if set(frappe.get_roles(frappe.session.user)).isdisjoint(YARD_OPERATOR_ROLES):
		frappe.throw(_("You are not authorised to record yard placements."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def yard_overview(depot=None):
	"""GET /api/v1/ess/yard-overview — branch-scoped zones + per-depot rollup.

	Zones are restricted to the user's allowed depots (``get_user_depots``; ``None``
	= all branches). ``depots`` carries a per-depot occupancy rollup that drives the
	PWA's depot accordion headers; ``zones`` is the flat list grouped per depot/block.
	"""
	_require_authenticated_user()
	allowed = get_user_depots()
	if depot and allowed is not None and depot not in allowed:
		return {"success": True, "zones": [], "depots": []}
	zones = yard.zone_occupancy(depot=depot, depots=None if depot else allowed)

	rollup = yard.depot_rollup(zones)
	codes = list(dict.fromkeys(z["depot"] for z in zones if z["depot"]))
	meta = (
		{
			d.name: d
			for d in frappe.get_all(
				"Depot", filters={"name": ["in", codes]}, fields=["name", "depot_name", "branch"]
			)
		}
		if codes
		else {}
	)
	depots = [
		{
			"code": c,
			"name": meta.get(c, frappe._dict()).depot_name or c,
			"branch": meta.get(c, frappe._dict()).branch,
			**rollup.get(
				c, {"occupied": 0, "capacity": 0, "utilization": None, "full_count": 0, "zone_count": 0}
			),
		}
		for c in codes
	]

	return {"success": True, "zones": zones, "depots": depots}


@frappe.whitelist(methods=["GET"])
def yard_zone_tanks(zone, search=None, start=0, page_length=50):
	"""GET /api/v1/ess/yard-zone-tanks — containers currently in one zone.

	Returns exactly the tanks the zone's occupancy bar counts (membership by yard_zone),
	so the list never disagrees with ``X/Y``. The zone is branch-checked (its depot must
	be in the caller's branch scope); within it, every tank is listed regardless of the
	container's own (possibly blank/stale) depot.
	"""
	_require_authenticated_user()
	z = frappe.db.get_value("Yard Zone", zone, ["name", "depot"], as_dict=True)
	if not z:
		return {"success": True, "total": 0, "start": cint(start), "page_length": cint(page_length) or 50, "items": []}
	assert_in_user_branch(depot=z.depot)
	return yard.zone_tank_list(zone, search=search, start=start, page_length=page_length)


@frappe.whitelist(methods=["GET"])
def yard_history(start=0, page_length=10, search=None):
	"""GET /api/v1/ess/yard-history — Container Movement (yard) history, depot-scoped."""
	_require_authenticated_user()
	return yard.list_yard_history(start=start, page_length=page_length, search=search)


@frappe.whitelist(methods=["GET"])
def movement_detail(name=None):
	"""GET /api/v1/ess/movement-detail — one Container Movement record's full detail."""
	_require_authenticated_user()
	return yard.get_movement_detail(name)


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
