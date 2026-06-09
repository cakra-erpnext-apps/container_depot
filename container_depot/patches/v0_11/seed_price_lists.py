"""Pricing spec §3.3 — seed per-principal selling Price Lists.

Each principal gets its own Price List carrying its own currency (per-principal
currency). OAK and Bertschi rate cards are in USD (ex-VAT 11%); local principals
default to IDR pending their own contracted rate cards.

Idempotent: existing price lists are kept.
"""

from __future__ import annotations

import frappe

# (name, currency).
PRICE_LISTS = [
	("OAK 2026", "USD"),
	("Bertschi 2026", "USD"),
	# Local principals: currency to be confirmed per contract.
	("Stolt 2026", "IDR"),
	("CIMI 2026", "IDR"),
	("NCS 2026", "IDR"),
]


def execute():
	created = 0
	for name, currency in PRICE_LISTS:
		if not frappe.db.exists("Currency", currency):
			print(f"[container_depot] seed_price_lists: currency {currency} missing; skipped {name}.")
			continue
		if frappe.db.exists("Price List", name):
			continue
		frappe.get_doc({
			"doctype": "Price List",
			"price_list_name": name,
			"currency": currency,
			"selling": 1,
			"buying": 0,
			"enabled": 1,
		}).insert(ignore_permissions=True)
		created += 1

	frappe.db.commit()
	print(f"[container_depot] seed_price_lists: created {created}, ensured {len(PRICE_LISTS)} price list(s).")
