"""Tests for the Depot Contract / Tariff Rate doctypes."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from container_depot.operations.doctype.depot_contract.depot_contract import (
	get_active_contract,
)
from container_depot.tests.test_api import ensure_test_customer


CUSTOMER_NAME = "Depot Contract Test Co"


def _make_contract(**overrides) -> frappe.model.document.Document:
	defaults = {
		"doctype": "Depot Contract",
		"customer": ensure_test_customer(CUSTOMER_NAME),
		"status": "Draft",
		"payment_type": "Cash",
		"valid_from": today(),
		"valid_to": add_days(today(), 365),
	}
	defaults.update(overrides)
	return frappe.get_doc(defaults)


class TestDepotContract(FrappeTestCase):
	def tearDown(self):
		# Per-test cleanup so get_active_contract isn't polluted by previous tests.
		frappe.db.delete("Depot Contract", {"customer": ensure_test_customer(CUSTOMER_NAME)})
		frappe.db.commit()
		super().tearDown()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("Depot Contract", {"customer": ensure_test_customer(CUSTOMER_NAME)})
		frappe.db.commit()
		super().tearDownClass()

	def test_cash_contract_minimal(self):
		c = _make_contract()
		c.insert(ignore_permissions=True)
		self.assertEqual(c.payment_type, "Cash")
		self.assertEqual(c.payment_terms, None)

	def test_top_contract_requires_terms(self):
		c = _make_contract(payment_type="TOP", credit_limit=1_000_000)
		with self.assertRaises(frappe.ValidationError):
			c.insert(ignore_permissions=True)

	def test_top_contract_requires_credit_limit(self):
		c = _make_contract(payment_type="TOP", payment_terms="NET 30", credit_limit=0)
		with self.assertRaises(frappe.ValidationError):
			c.insert(ignore_permissions=True)

	def test_valid_to_must_follow_valid_from(self):
		c = _make_contract(valid_to=add_days(today(), -1))
		with self.assertRaises(frappe.ValidationError):
			c.insert(ignore_permissions=True)

	def test_active_status_requires_tariff_lines(self):
		c = _make_contract(status="Active")
		with self.assertRaises(frappe.ValidationError):
			c.insert(ignore_permissions=True)

	def test_active_contract_with_tariff_lines_ok(self):
		c = _make_contract(
			status="Active",
			tariff_lines=[{"service": "Lift Off", "uom": "container", "rate": 250000, "currency": "IDR"}],
		)
		c.insert(ignore_permissions=True)
		self.assertEqual(c.status, "Active")
		self.assertEqual(len(c.tariff_lines), 1)

	def test_get_active_contract_returns_active(self):
		_make_contract(
			status="Draft",
			tariff_lines=[{"service": "Cleaning", "uom": "container", "rate": 100000, "currency": "IDR"}],
		).insert(ignore_permissions=True)
		_make_contract(
			status="Active",
			payment_type="TOP",
			payment_terms="NET 45",
			credit_limit=5_000_000,
			tariff_lines=[{"service": "Lift Off", "uom": "container", "rate": 250000, "currency": "IDR"}],
		).insert(ignore_permissions=True)

		hit = get_active_contract(ensure_test_customer(CUSTOMER_NAME))
		self.assertIsNotNone(hit)
		self.assertEqual(hit.payment_type, "TOP")
		self.assertEqual(hit.payment_terms, "NET 45")


class TestContainerPrincipalLink(FrappeTestCase):
	"""Quick sanity: Container.principal must accept a Customer name."""

	CONTAINER_NO = "TSTU2222220"  # ISO 11 chars total when stripped

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.customer = ensure_test_customer("Container Principal Link Test Co")

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("Container", {"container_no": cls.CONTAINER_NO})
		frappe.db.commit()
		super().tearDownClass()

	def test_container_principal_links_to_customer(self):
		c = frappe.get_doc({
			"doctype": "Container",
			"container_no": self.CONTAINER_NO,
			"container_type": "ISO Tank",
			"status": "Available",
			"principal": self.customer,
		})
		c.insert(ignore_permissions=True)
		self.assertEqual(c.principal, self.customer)
