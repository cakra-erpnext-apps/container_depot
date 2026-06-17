"""Cash booking auto-approve + revert-to-draft, and the gate's submit/payment block.

- A paid Cash invoice auto-submits (confirms) its booking.
- Revert-to-draft reopens a confirmed booking for editing WITHOUT reversing payment,
  and is refused once a Booking Code has been consumed at the gate.
- The gate detail reports why it is blocked (cash unpaid vs paid-but-not-submitted).

All fixtures are torn down per test (FrappeTestCase rollback + customer-world cleanup).
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from container_depot.api import _booking_gate_detail
from container_depot.operations.doctype.container_booking.container_booking import (
	revert_booking_to_draft,
	sync_bookings_for_invoice,
)
from container_depot.tests.test_api import ensure_test_customer
from container_depot.tests.test_container_booking import (
	_cleanup_customer_world,
	_make_active_contract,
)
from container_depot.tests.test_phase9_booking_refine import _ensure_test_depot


class TestCashAutoApproveAndGate(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		_ensure_test_depot()
		self.customer = ensure_test_customer("CashGate Customer")
		_cleanup_customer_world(self.customer)
		self.contract = _make_active_contract(self.customer, payment_type="Cash")

	def tearDown(self):
		_cleanup_customer_world(self.customer)
		frappe.db.rollback()

	def _draft_cash_booking(self):
		return frappe.get_doc({
			"doctype": "Container Booking",
			"direction": "Tank In",
			"customer": self.customer,
			"contract": self.contract,
			"booking_status": "Pending Payment",
			"do_reference": "DO-CASHGATE",
			"items": [{"container_no": "CASHGATE001"}],
		}).insert(ignore_permissions=True)

	def _pay(self, si):
		frappe.db.set_value("Sales Invoice", si, {"docstatus": 1, "status": "Paid", "outstanding_amount": 0})

	# --- auto-approve ---------------------------------------------------------
	def test_cash_paid_auto_submits_booking(self):
		b = self._draft_cash_booking()
		self._pay(b.sales_invoice)
		sync_bookings_for_invoice(b.sales_invoice)
		b.reload()
		self.assertEqual(b.docstatus, 1)
		self.assertEqual(b.booking_status, "Confirmed")
		self.assertEqual(b.payment_status, "Paid")
		# Confirmation issues the gate codes.
		self.assertTrue(frappe.get_all("Booking Code", filters={"booking": b.name}, pluck="name"))

	# --- revert to draft (keeps payment) -------------------------------------
	def test_revert_to_draft_keeps_payment_and_allows_resubmit(self):
		b = self._draft_cash_booking()
		self._pay(b.sales_invoice)
		sync_bookings_for_invoice(b.sales_invoice)
		b.reload()
		self.assertEqual(b.docstatus, 1)
		si = b.sales_invoice

		revert_booking_to_draft(b.name)
		b.reload()
		self.assertEqual(b.docstatus, 0)
		self.assertEqual(b.booking_status, "Pending Confirmation")
		# Payment untouched: same invoice, still submitted/paid.
		self.assertEqual(b.sales_invoice, si)
		self.assertEqual(frappe.db.get_value("Sales Invoice", si, "docstatus"), 1)

		# Re-submit succeeds (payment already settled) and re-confirms.
		b.flags.ignore_permissions = True
		b.submit()
		self.assertEqual(b.docstatus, 1)
		self.assertEqual(b.booking_status, "Confirmed")

	def test_revert_refused_when_a_code_is_used(self):
		b = self._draft_cash_booking()
		self._pay(b.sales_invoice)
		sync_bookings_for_invoice(b.sales_invoice)
		b.reload()
		code = frappe.get_all("Booking Code", filters={"booking": b.name}, pluck="name")[0]
		frappe.db.set_value("Booking Code", code, "state", "Used", update_modified=False)
		with self.assertRaises(frappe.ValidationError):
			revert_booking_to_draft(b.name)

	# --- gate block reasons ---------------------------------------------------
	def test_gate_blocked_cash_unpaid(self):
		b = self._draft_cash_booking()  # draft + unpaid
		d = _booking_gate_detail(b.name)
		self.assertFalse(d["booking_submitted"])
		self.assertEqual(d["block_reason"], "cash_unpaid")

	def test_gate_blocked_paid_but_not_submitted(self):
		b = self._draft_cash_booking()
		# Paid but still a draft (stands in for an auto-submit that couldn't go through).
		frappe.db.set_value("Container Booking", b.name, "payment_status", "Paid", update_modified=False)
		d = _booking_gate_detail(b.name)
		self.assertFalse(d["booking_submitted"])
		self.assertEqual(d["block_reason"], "not_submitted")

	def test_gate_not_blocked_when_submitted(self):
		b = self._draft_cash_booking()
		self._pay(b.sales_invoice)
		sync_bookings_for_invoice(b.sales_invoice)  # auto-submits
		b.reload()
		d = _booking_gate_detail(b.name)
		self.assertTrue(d["booking_submitted"])
		self.assertIsNone(d["block_reason"])
