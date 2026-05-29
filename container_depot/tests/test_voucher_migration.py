"""Tests the Voucher → Booking migration patch (Phase 5a)."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from container_depot.patches.v0_5.voucher_to_booking import execute as run_migration
from container_depot.tests.test_api import ensure_test_customer


VOUCHER_PREFIX = "VOUCH-MIG-"


def _seed_voucher(idx: int, *, voucher_type: str, payment_status: int, customer: str, containers: list[str]):
	if frappe.db.exists("Voucher", {"voucher_id": f"{VOUCHER_PREFIX}{idx}"}):
		return
	frappe.get_doc({
		"doctype": "Voucher",
		"voucher_id": f"{VOUCHER_PREFIX}{idx}",
		"voucher_type": voucher_type,
		"client": customer,
		"principal": customer,
		"payment_status": payment_status,
		"status": "Active",
		"expected_containers": [
			{"container_no": cn, "container_type": "ISO Tank", "status": "Expected"}
			for cn in containers
		],
	}).insert(ignore_permissions=True)


class TestVoucherMigration(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.customer = ensure_test_customer("VoucherMigration Test Customer")
		# Clear any prior migration artifacts so the test is deterministic.
		_purge_migration_world(cls.customer)
		_seed_voucher(1, voucher_type="Gate_In (Bon Bongkar)", payment_status=1, customer=cls.customer, containers=["MIGU1110001", "MIGU1110002"])
		_seed_voucher(2, voucher_type="Gate_Out (Release)", payment_status=1, customer=cls.customer, containers=["MIGU2220001"])
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		_purge_migration_world(cls.customer)
		super().tearDownClass()

	def test_migration_creates_expected_records(self):
		pre_b = frappe.db.count("Isotank Booking", filters={"customer": self.customer})
		pre_c = frappe.db.count("Booking Code")
		pre_bk = frappe.db.count("Order Bongkar")
		pre_mt = frappe.db.count("Order Muat")

		run_migration()

		post_b = frappe.db.count("Isotank Booking", filters={"customer": self.customer})
		self.assertEqual(post_b - pre_b, 2, "expected 2 new Isotank Bookings")

		post_c = frappe.db.count("Booking Code")
		post_bk = frappe.db.count("Order Bongkar")
		post_mt = frappe.db.count("Order Muat")
		# 2 + 1 = 3 expected children → 3 codes, 2 Bongkar + 1 Muat.
		self.assertEqual(post_c - pre_c, 3, "expected 3 new Booking Codes")
		self.assertEqual(post_bk - pre_bk, 2, "expected 2 new Order Bongkar")
		self.assertEqual(post_mt - pre_mt, 1, "expected 1 new Order Muat")

	def test_migration_is_idempotent(self):
		run_migration()
		first_b = frappe.db.count("Isotank Booking", filters={"customer": self.customer})
		first_c = frappe.db.count("Booking Code")
		run_migration()  # second time should add nothing for these vouchers
		self.assertEqual(frappe.db.count("Isotank Booking", filters={"customer": self.customer}), first_b)
		self.assertEqual(frappe.db.count("Booking Code"), first_c)


def _purge_migration_world(customer: str):
	bookings = frappe.get_all("Isotank Booking", filters={"customer": customer}, pluck="name")
	if bookings:
		codes = frappe.get_all("Booking Code", filters={"booking": ("in", bookings)}, pluck="name")
		if codes:
			frappe.db.delete("Order Bongkar", {"booking_code": ("in", codes)})
			frappe.db.delete("Order Muat", {"booking_code": ("in", codes)})
		frappe.db.delete("Booking Code", {"booking": ("in", bookings)})
		frappe.db.delete("Isotank Booking Item", {"parent": ("in", bookings)})
		frappe.db.delete("Isotank Booking", {"name": ("in", bookings)})
	# Vouchers
	frappe.db.delete("Voucher Container", {"parent": ("like", f"%{VOUCHER_PREFIX}%")})
	frappe.db.delete("Voucher", {"voucher_id": ("like", f"{VOUCHER_PREFIX}%")})
	frappe.db.commit()
