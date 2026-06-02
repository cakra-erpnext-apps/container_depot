"""Tests for the three Phase-3 critical controllers:

1. TOP credit-block (Isotank Booking.before_submit).
2. TANK OUT gating (Isotank Booking.validate when direction == 'Tank Out').
3. 72h Booking Code expiry (container_depot.tasks.expire_booking_codes).
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime, today

from container_depot.tasks import expire_booking_codes
from container_depot.tests.test_api import ensure_test_customer


CUSTOMER_CASH = "Phase3 Cash Customer"
CUSTOMER_TOP = "Phase3 TOP Customer"
CONTAINER_NO = "TSTU3334440"


def _cleanup_customer_world(customer: str):
	bookings = frappe.get_all("Isotank Booking", filters={"customer": customer}, pluck="name")
	if bookings:
		frappe.db.delete("Booking Code", {"booking": ("in", bookings)})
		frappe.db.delete("Isotank Booking Item", {"parent": ("in", bookings)})
		frappe.db.delete("Isotank Booking", {"name": ("in", bookings)})
	contracts = frappe.get_all("Depot Contract", filters={"customer": customer}, pluck="name")
	if contracts:
		frappe.db.delete("Tariff Rate", {"parent": ("in", contracts)})
		frappe.db.delete("Depot Contract", {"name": ("in", contracts)})
	frappe.db.commit()


def _make_active_contract(customer: str, *, payment_type: str, credit_limit=0, payment_terms=None) -> str:
	doc = frappe.get_doc({
		"doctype": "Depot Contract",
		"customer": customer,
		"status": "Active",
		"payment_type": payment_type,
		"payment_terms": payment_terms,
		"credit_limit": credit_limit,
		"valid_from": today(),
		"valid_to": add_days(today(), 365),
		"tariff_lines": [{"service": "Lift Off", "uom": "container", "rate": 250000, "currency": "IDR"}],
	}).insert(ignore_permissions=True)
	return doc.name


class TestTopCreditBlock(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.customer = ensure_test_customer(CUSTOMER_TOP)
		_cleanup_customer_world(cls.customer)
		cls.contract = _make_active_contract(
			cls.customer, payment_type="TOP", credit_limit=1_000_000, payment_terms="NET 30"
		)

	@classmethod
	def tearDownClass(cls):
		_cleanup_customer_world(cls.customer)
		super().tearDownClass()

	def _booking(self):
		return frappe.get_doc({
			"doctype": "Isotank Booking",
			"direction": "Tank In",
			"customer": self.customer,
			"contract": self.contract,
			"booking_status": "Pending Confirmation",
			"items": [{"container_no": "TANK0000001"}],
		})

	def test_top_block_over_credit_limit(self):
		# Stub the outstanding-amount SQL to look "over limit" without seeding invoices.
		original_sql = frappe.db.sql

		def fake_sql(query, *args, **kwargs):
			if "SUM(outstanding_amount)" in query and "tabSales Invoice" in query:
				return [[2_000_000]]
			return original_sql(query, *args, **kwargs)

		frappe.db.sql = fake_sql
		try:
			b = self._booking()
			b.insert(ignore_permissions=True)
			with self.assertRaises(frappe.ValidationError):
				b.submit()
			b.reload()
			self.assertEqual(b.booking_status, "Blocked")
			self.assertIn("credit", (b.block_reason or "").lower())
		finally:
			frappe.db.sql = original_sql

	def test_top_block_overdue_invoice(self):
		original_count = frappe.db.count

		def fake_count(doctype, filters=None, *a, **kw):
			if doctype == "Sales Invoice" and filters and filters.get("status") == "Overdue":
				return 1
			return original_count(doctype, filters=filters, *a, **kw)

		frappe.db.count = fake_count
		try:
			b = self._booking()
			b.insert(ignore_permissions=True)
			with self.assertRaises(frappe.ValidationError):
				b.submit()
			b.reload()
			self.assertEqual(b.booking_status, "Blocked")
			self.assertIn("overdue", (b.block_reason or "").lower())
		finally:
			frappe.db.count = original_count


class TestCashPaidInvoice(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.customer = ensure_test_customer(CUSTOMER_CASH)
		_cleanup_customer_world(cls.customer)
		cls.contract = _make_active_contract(cls.customer, payment_type="Cash")

	@classmethod
	def tearDownClass(cls):
		_cleanup_customer_world(cls.customer)
		super().tearDownClass()

	def test_cash_booking_blocked_without_invoice(self):
		b = frappe.get_doc({
			"doctype": "Isotank Booking",
			"direction": "Tank In",
			"customer": self.customer,
			"contract": self.contract,
			"booking_status": "Pending Confirmation",
			"items": [{"container_no": "TANK0000002"}],
		})
		b.insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			b.submit()
		b.reload()
		self.assertEqual(b.booking_status, "Blocked")


class TestTankOutGating(FrappeTestCase):
	"""Direction=Tank Out requires every item Container to be Ready + have a
	valid Cleaning Certificate."""

	CUSTOMER = "Phase3 TankOut Customer"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.customer = ensure_test_customer(cls.CUSTOMER)
		_cleanup_customer_world(cls.customer)
		cls.contract = _make_active_contract(cls.customer, payment_type="Cash")
		# Seed a Container in Ready_For_Service.
		if not frappe.db.exists("Container", CONTAINER_NO):
			frappe.get_doc({
				"doctype": "Container",
				"container_no": CONTAINER_NO,
				"container_type": "ISO Tank",
				"status": "Ready_For_Service",
				"principal": cls.customer,
			}).insert(ignore_permissions=True)
		cls.container = CONTAINER_NO

	@classmethod
	def tearDownClass(cls):
		_cleanup_customer_world(cls.customer)
		# Clean up cleaning certs + container created here.
		frappe.db.delete("Cleaning Certificate", {"container": cls.container})
		frappe.db.delete("Container", {"container_no": cls.container})
		frappe.db.commit()
		super().tearDownClass()

	def _booking(self):
		return frappe.get_doc({
			"doctype": "Isotank Booking",
			"direction": "Tank Out",
			"customer": self.customer,
			"contract": self.contract,
			"booking_status": "Pending Confirmation",
			"items": [{"container": self.container}],
		})

	def test_tank_out_blocked_without_clean_cert(self):
		frappe.db.delete("Cleaning Certificate", {"container": self.container})
		frappe.db.commit()
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._booking().insert(ignore_permissions=True)
		self.assertIn("Cleaning Certificate", str(ctx.exception))

	def test_tank_out_blocked_with_expired_cert(self):
		frappe.db.delete("Cleaning Certificate", {"container": self.container})
		cert = frappe.get_doc({
			"doctype": "Cleaning Certificate",
			"container": self.container,
			"clean_date": add_days(today(), -90),
			"valid_until": add_days(today(), -1),  # expired yesterday
			"cleaning_method": "Steam Wash",
		})
		cert.insert(ignore_permissions=True)
		cert.submit()
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._booking().insert(ignore_permissions=True)
		self.assertIn("expired", str(ctx.exception).lower())

	def test_tank_out_passes_with_valid_cert(self):
		frappe.db.delete("Cleaning Certificate", {"container": self.container})
		cert = frappe.get_doc({
			"doctype": "Cleaning Certificate",
			"container": self.container,
			"clean_date": now_datetime(),
			"cleaning_method": "Hot Water",
		})
		cert.insert(ignore_permissions=True)
		cert.submit()  # default valid_until = today + 30
		b = self._booking()
		b.insert(ignore_permissions=True)  # should NOT raise
		self.assertEqual(b.direction, "Tank Out")

	def test_tank_out_blocked_when_container_not_ready(self):
		frappe.db.set_value("Container", self.container, "status", "In_Workshop")
		try:
			frappe.db.delete("Cleaning Certificate", {"container": self.container})
			cert = frappe.get_doc({
				"doctype": "Cleaning Certificate",
				"container": self.container,
				"clean_date": now_datetime(),
				"cleaning_method": "Hot Water",
			})
			cert.insert(ignore_permissions=True)
			cert.submit()
			with self.assertRaises(frappe.ValidationError) as ctx:
				self._booking().insert(ignore_permissions=True)
			self.assertIn("Ready", str(ctx.exception))
		finally:
			frappe.db.set_value("Container", self.container, "status", "Ready_For_Service")


class TestBookingCodeExpiry(FrappeTestCase):
	"""Scheduler-style expiry: Active codes whose expires_at < now → Expired."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.customer = ensure_test_customer("Phase3 Expiry Customer")
		_cleanup_customer_world(cls.customer)
		cls.contract = _make_active_contract(cls.customer, payment_type="Cash")

	@classmethod
	def tearDownClass(cls):
		_cleanup_customer_world(cls.customer)
		super().tearDownClass()

	def test_expire_booking_codes_flips_stale(self):
		# Create a booking + code with expires_at in the past.
		from container_depot.operations.doctype.booking_code.booking_code import (
			CODE_TTL_HOURS,
			generate_code,
		)
		b = frappe.get_doc({
			"doctype": "Isotank Booking",
			"direction": "Tank In",
			"customer": self.customer,
			"contract": self.contract,
			"booking_status": "Pending Confirmation",
			"items": [{"container_no": "TANK0000099"}],
		}).insert(ignore_permissions=True)
		code = frappe.get_doc({
			"doctype": "Booking Code",
			"code": generate_code(),
			"booking": b.name,
			"direction": "Tank In",
			"container_no": "TANK0000099",
			"state": "Active",
			"issued_at": add_to_date(now_datetime(), hours=-(CODE_TTL_HOURS + 1)),
			"expires_at": add_to_date(now_datetime(), hours=-1),
		}).insert(ignore_permissions=True)

		expired = expire_booking_codes()
		self.assertGreaterEqual(expired, 1)
		code.reload()
		self.assertEqual(code.state, "Expired")

	def test_expire_booking_codes_leaves_active_alone(self):
		from container_depot.operations.doctype.booking_code.booking_code import (
			generate_code,
		)
		b = frappe.get_doc({
			"doctype": "Isotank Booking",
			"direction": "Tank In",
			"customer": self.customer,
			"contract": self.contract,
			"booking_status": "Pending Confirmation",
			"items": [{"container_no": "TANK0000098"}],
		}).insert(ignore_permissions=True)
		code = frappe.get_doc({
			"doctype": "Booking Code",
			"code": generate_code(),
			"booking": b.name,
			"direction": "Tank In",
			"container_no": "TANK0000098",
			"state": "Active",
			"issued_at": now_datetime(),
			"expires_at": add_to_date(now_datetime(), hours=+5),
		}).insert(ignore_permissions=True)
		expire_booking_codes()
		code.reload()
		self.assertEqual(code.state, "Active")
