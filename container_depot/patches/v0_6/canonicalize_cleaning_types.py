"""PRD v0.2 §2 — cleaning multi-jenis: re-map legacy cleaning values.

v0.2 unifies Cleaning Order.cleaning_type and Cleaning Certificate.cleaning_method
onto one canonical wash list that includes PP Wash, Methanol Rinse and Steam
Wash. This patch rewrites the old free-Select values onto the canonical names so
existing rows stay valid.

Idempotent: values already canonical are left untouched.
"""

from __future__ import annotations

import frappe

# legacy Cleaning Order.cleaning_type -> canonical
ORDER_MAP = {
	"Standard_Wash": "Detergent",
	"Hot_Wash": "Hot Water",
	"Steam_Clean": "Steam Wash",
	"Chemical_Clean": "Chemical",
	"Nitrogen_Purge": "Nitrogen Purge",
}

# legacy Cleaning Certificate.cleaning_method -> canonical
CERT_MAP = {
	"Hot Water": "Hot Water",
	"Steam": "Steam Wash",
	"Chemical Wash": "Chemical",
	"Detergent": "Detergent",
}


def execute():
	_remap("Cleaning Order", "cleaning_type", ORDER_MAP)
	_remap("Cleaning Certificate", "cleaning_method", CERT_MAP)
	frappe.db.commit()


def _remap(doctype: str, field: str, mapping: dict[str, str]):
	for legacy, canonical in mapping.items():
		if legacy == canonical:
			continue
		frappe.db.sql(
			f"UPDATE `tab{doctype}` SET `{field}`=%s WHERE `{field}`=%s",
			(canonical, legacy),
		)
