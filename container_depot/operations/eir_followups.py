"""Follow-up work derivable from a submitted EIR — detection + creation logic ONLY.

The wiring (when/where to fire these) is intentionally left to the caller: nothing here
is hooked into ``Inspection.on_submit`` or any menu. Call these from wherever you decide.

Rules (per ops):
- **Cleaning Order**  ← an EIR whose ``tank_status`` is ``Empty Dirty``.
- **Repair Order (M&R)** ← an EIR with at least one *real* Inspection Damage Entry — a
  row whose damage is other than Acceptable (``v``) or whose repair is other than No
  Action (``X``). (With the new checklist default these rows aren't even stored unless
  they are findings, but the filter is applied defensively for older / Desk-entered data.)
"""

from __future__ import annotations

import frappe

from container_depot.operations.eir import ACCEPTABLE_DAMAGE_CODE, NO_ACTION_REPAIR_CODE

EMPTY_DIRTY = "Empty Dirty"

# Container Movement-style copy guard for child rows.
_ROW_EXCLUDE = {
	"name", "parent", "parentfield", "parenttype", "idx",
	"owner", "creation", "modified", "modified_by", "docstatus", "doctype",
}


# --- detection ---------------------------------------------------------------
def eir_needs_cleaning(inspection) -> bool:
	"""True when the EIR's tank condition is Empty Dirty (→ a Cleaning Order is due)."""
	return frappe.db.get_value("Inspection", inspection, "tank_status") == EMPTY_DIRTY


def eir_real_damage_rows(inspection) -> list:
	"""Inspection Damage Entry rows of ``inspection`` that are real findings — damage
	other than Acceptable, or repair other than No Action."""
	rows = frappe.get_all(
		"Inspection Damage Entry",
		filters={"parent": inspection, "parenttype": "Inspection"},
		fields=[
			"name", "checklist_item", "damage_type", "repair_code",
			"damage_description", "severity", "area", "component",
		],
		order_by="idx asc",
	)
	out = []
	for r in rows:
		real_damage = r.damage_type and r.damage_type != ACCEPTABLE_DAMAGE_CODE
		real_repair = r.repair_code and r.repair_code != NO_ACTION_REPAIR_CODE
		if real_damage or real_repair:
			out.append(r)
	return out


def eir_needs_mr(inspection) -> bool:
	"""True when the EIR has at least one real damage/repair finding (→ M&R is due)."""
	return bool(eir_real_damage_rows(inspection))


# --- creation (idempotent; NOT auto-called) ----------------------------------
def create_cleaning_order_from_eir(inspection, ignore_permissions=True):
	"""Create a Pending Cleaning Order for an Empty-Dirty EIR's container. Idempotent:
	returns the existing open order (Pending / In_Progress) if one already exists.
	Returns the Cleaning Order name, or ``None`` when no cleaning is due."""
	insp = frappe.db.get_value(
		"Inspection", inspection, ["container", "tank_status", "depot"], as_dict=True
	)
	if not insp or not insp.container or insp.tank_status != EMPTY_DIRTY:
		return None
	existing = frappe.db.exists(
		"Cleaning Order", {"container": insp.container, "status": ["in", ["Pending", "In_Progress"]]}
	)
	if existing:
		return existing
	co = frappe.new_doc("Cleaning Order")
	co.container = insp.container
	co.inspection = inspection  # EIR -> Cleaning Order -> Certificate
	co.status = "Pending"
	# Carry the depot (for branch-scoped notifications) — from the EIR, else the container.
	depot = insp.depot or frappe.db.get_value("Container", insp.container, "depot")
	if depot and co.meta.has_field("depot"):
		co.depot = depot
	co.insert(ignore_permissions=ignore_permissions)
	return co.name


def create_repair_order_from_eir(inspection, ignore_permissions=True):
	"""Create a Pending-Approval Repair Order (M&R) for an EIR with real damage findings.
	Idempotent per source EIR (one Repair Order per ``inspection``). Carries the EIR's
	``repair_estimate`` rows if present. Returns the Repair Order name, or ``None`` when
	there is nothing to repair."""
	if not eir_needs_mr(inspection):
		return None
	existing = frappe.db.get_value("Repair Order", {"inspection": inspection}, "name")
	if existing:
		return existing
	insp = frappe.get_doc("Inspection", inspection)
	ro = frappe.new_doc("Repair Order")
	ro.container = insp.container
	ro.inspection = insp.name
	ro.status = "Pending Approval"
	ro.billing_status = "Unbilled"
	for row in (insp.repair_estimate or []):
		ro.append("estimation_items", {k: v for k, v in row.as_dict().items() if k not in _ROW_EXCLUDE})
	ro.insert(ignore_permissions=ignore_permissions)
	return ro.name
