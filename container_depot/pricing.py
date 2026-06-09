"""Tariff-driven pricing helpers.

Prices come from the customer's active ``Depot Contract`` tariff lines (the
``Tariff Rate`` child table, keyed by **Item**: item / uom / rate / manhour_rate
/ qty). Billing resolves a negotiated rate by Item code, so a contract change
flows straight through to new orders. The service Items themselves (``Lift On``,
``Lift Off``, ``Storage per Day``, the cleaning grades, …) are the seeded catalog
Items priced per principal via Item Price.
"""

from __future__ import annotations

import frappe

# Order type (portal vocabulary) -> canonical service Item code. None = not
# priced by the contract tariff (the Cashier fills the rate in on the invoice).
ITEM_FOR_ORDER_TYPE = {
	"Lift On": "Lift On",
	"Lift Off": "Lift Off",
	"Periodic Test": "Periodic Test 2.5 Year",
	"Leak Test": "Leak Test 1 Bar",
	"Haulage": None,
}

# Canonical service Item codes used by the consolidated / monthly billing path.
# These match the codes seeded by patches.v0_11.seed_service_items.
LIFT_ON_ITEM = "Lift On"
LIFT_OFF_ITEM = "Lift Off"
STORAGE_ITEM = "Storage per Day"
# Representative cleaning charge billed per Cleaning Order. Adjust to the grade a
# customer's rate card actually negotiates if cleaning is priced per wash type.
CLEANING_ITEM = "Standard Cleaning"


def resolve_tariff_rate(contract, item):
	"""Return the negotiated rate for ``item`` on ``contract`` (0 if none).

	Rates are resolved from Item Price (single source of truth): an Active contract
	publishes its agreed lines to a customer Price List (``generated_price_list``),
	and billing reads that list — the same path walk-in pricing uses.
	"""
	if not contract or not item:
		return 0
	price_list = frappe.db.get_value("Depot Contract", contract, "generated_price_list")
	if not price_list:
		return 0
	from container_depot import pricing_model

	return pricing_model.resolve_price(item, price_list) or 0


def contract_for_order(order):
	"""Resolve the Depot Contract behind an Order Bongkar / Muat via its code."""
	if not order.get("booking_code"):
		return None
	booking = frappe.db.get_value("Booking Code", order.booking_code, "booking")
	if not booking:
		return None
	return frappe.db.get_value("Container Booking", booking, "contract")


def order_amount(order):
	"""(total, unit_rate) for an order. Uses the order's own price_per_container
	when set, else the contract tariff for the mapped service Item."""
	qty = order.get("quantity") or 1
	rate = order.get("price_per_container") or 0
	if not rate:
		contract = contract_for_order(order)
		item = ITEM_FOR_ORDER_TYPE.get(order.get("order_type"))
		rate = resolve_tariff_rate(contract, item)
	return (rate or 0) * qty, (rate or 0)
