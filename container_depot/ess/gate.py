"""ESS PWA Gate Entry endpoints — thin ``@frappe.whitelist`` wrappers over operations.gate.

Per the integration rule (mirrors ``ess/inspections.py``): endpoints here only add auth +
whitelisting; all listing/detail logic lives in ``container_depot.operations.gate``.
"""

from __future__ import annotations

import frappe

from container_depot.api import _require_authenticated_user
from container_depot.operations import gate


@frappe.whitelist(methods=["GET"])
def gate_history(start=0, page_length=10, search=None):
	"""GET /api/v1/ess/gate-history — Gate Entry (in/out voucher) history, depot-scoped."""
	_require_authenticated_user()
	return gate.list_gate_history(start=start, page_length=page_length, search=search)


@frappe.whitelist(methods=["GET"])
def gate_detail(name=None):
	"""GET /api/v1/ess/gate-detail — one Gate Entry's full vehicle/order/EIR detail."""
	_require_authenticated_user()
	return gate.get_gate_detail(name)
