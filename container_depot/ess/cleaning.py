"""ESS PWA Cleaning Statement endpoints — thin ``@frappe.whitelist`` wrappers.

Per the integration rule (mirrors ``ess/inspections.py``): endpoints here only add
authentication + whitelisting + GET/POST gating; every bit of resolution/build logic
lives in ``container_depot.operations.cleaning`` so the same code backs the PWA and
any Desk / automation caller.
"""

from __future__ import annotations

import frappe

from container_depot.api import _require_authenticated_user
from container_depot.operations import cleaning


@frappe.whitelist(methods=["GET"])
def cleaning_masters():
	"""GET /api/v1/ess/cleaning-masters — checklist taxonomy + default remarks."""
	_require_authenticated_user()
	return cleaning.get_cleaning_masters()


@frappe.whitelist(methods=["GET"])
def cleaning_prefill(container=None, container_no=None, inspection=None):
	"""GET /api/v1/ess/cleaning-prefill?container_no=… — Container master auto-fill."""
	_require_authenticated_user()
	return cleaning.prefill(container=container, container_no=container_no, inspection=inspection)


@frappe.whitelist(methods=["GET"])
def cleaning_history(search=None, start=0, page_length=10, docstatus=None):
	"""GET /api/v1/ess/cleaning-history — the caller's own Cleaning Statements."""
	_require_authenticated_user()
	return cleaning.list_my_statements(
		user=frappe.session.user, search=search, start=start, page_length=page_length, docstatus=docstatus
	)


@frappe.whitelist(methods=["POST"])
def cleaning_create(
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
):
	"""POST /api/v1/ess/cleaning-create — build (and optionally submit) a statement."""
	_require_authenticated_user()
	return cleaning.create_cleaning_statement(
		container=container,
		inspection=inspection,
		date_of_issue=date_of_issue,
		place_of_issue=place_of_issue,
		gas_free=gas_free,
		o2_percent=o2_percent,
		lel_percent=lel_percent,
		seal_manhole=seal_manhole,
		seal_airline=seal_airline,
		seal_bottom_outlet=seal_bottom_outlet,
		remarks=remarks,
		signature=signature,
		results=results,
		submit=submit,
	)
