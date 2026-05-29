"""Isotank Booking — the booking spine for PRO-OPS-08 Tank In / Tank Out.

Carries the three Phase-3 critical controllers:

1. TOP credit-block (``before_submit``): TOP customers blocked when outstanding
   exceeds credit limit or any overdue Sales Invoice exists. Cash bookings
   require a *paid* linked Sales Invoice before submit.
2. TANK OUT gating (``validate`` when direction == 'Tank Out'): every item must
   reference a Container that is clean + ready, with a Cleaning Certificate
   whose ``valid_until`` covers today.
3. 72h Booking Code issuance on submit; expiry runs hourly via
   ``container_depot.tasks.expire_booking_codes`` (see hooks.py).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_to_date, getdate, now_datetime, today

from container_depot.operations.doctype.booking_code.booking_code import (
	CODE_TTL_HOURS,
	generate_code,
)
from container_depot.operations.doctype.depot_contract.depot_contract import (
	get_active_contract,
)


CONTAINER_READY_STATUSES = {"Available", "Ready_For_Service", "Ready_For_Release", "Ready"}


class IsotankBooking(Document):
	# ---- naming ---------------------------------------------------------
	def autoname(self):
		prefix = "BKG-IN-" if self.direction == "Tank In" else "BKG-OUT-"
		self.name = make_autoname(prefix + ".YYYY.-.#####")

	# ---- lifecycle ------------------------------------------------------
	def validate(self):
		self._sync_payment_type_from_contract()
		if self.direction == "Tank Out":
			self._validate_tank_out_gating()

	def before_submit(self):
		self._enforce_payment_rules()

	def on_submit(self):
		self._issue_booking_codes()
		self.db_set("booking_status", "Confirmed", update_modified=False)

	# ---- helpers --------------------------------------------------------
	def _sync_payment_type_from_contract(self):
		if not self.contract:
			return
		contract = frappe.db.get_value(
			"Depot Contract",
			self.contract,
			["customer", "payment_type", "status"],
			as_dict=True,
		)
		if not contract:
			frappe.throw(_("Contract {0} not found.").format(self.contract))
		if self.customer and contract.customer != self.customer:
			frappe.throw(_("Contract {0} belongs to a different customer.").format(self.contract))
		if contract.status != "Active":
			frappe.throw(_("Contract {0} is not Active (status={1}).").format(self.contract, contract.status))
		self.payment_type = contract.payment_type

	def _validate_tank_out_gating(self):
		"""TANK OUT requires every item to ref a clean+ready Container with a
		Cleaning Certificate that's still valid today.
		"""
		failures: list[str] = []
		for item in self.items or []:
			if not item.container:
				failures.append(
					_("Item for {0}: container link required for Tank Out.").format(
						item.container_no or "(no number)"
					)
				)
				continue
			c = frappe.db.get_value(
				"Container",
				item.container,
				["status", "container_no"],
				as_dict=True,
			)
			if not c:
				failures.append(_("Container {0} not found.").format(item.container))
				continue
			if c.status not in CONTAINER_READY_STATUSES:
				failures.append(
					_("Container {0} is not Ready (status={1}).").format(c.container_no, c.status)
				)
				continue
			cert = frappe.db.get_value(
				"Cleaning Certificate",
				{
					"container": item.container,
					"docstatus": 1,
				},
				["name", "valid_until"],
				as_dict=True,
				order_by="clean_date desc",
			)
			if not cert:
				failures.append(
					_("Container {0} has no submitted Cleaning Certificate.").format(c.container_no)
				)
				continue
			if cert.valid_until and getdate(cert.valid_until) < getdate(today()):
				failures.append(
					_("Container {0} cleaning cert {1} expired on {2}.").format(
						c.container_no, cert.name, cert.valid_until
					)
				)

		if failures:
			frappe.throw("<br>".join(failures))

	def _enforce_payment_rules(self):
		"""TOP: outstanding + credit limit + overdue check via ERPNext.
		Cash: linked Sales Invoice must be Paid.
		"""
		contract = get_active_contract(self.customer)
		if not contract:
			self._block(_("Customer has no Active contract."))

		payment_type = contract.payment_type
		if payment_type == "Cash":
			self._enforce_cash_paid_invoice()
		elif payment_type == "TOP":
			self._enforce_top_credit(contract)
		else:
			frappe.throw(_("Unknown payment type {0}.").format(payment_type))

	def _enforce_cash_paid_invoice(self):
		if not self.sales_invoice:
			self._block(_("Cash booking requires a paid Sales Invoice before submit."))
		status, docstatus = frappe.db.get_value(
			"Sales Invoice", self.sales_invoice, ["status", "docstatus"]
		) or (None, None)
		if docstatus != 1:
			self._block(_("Sales Invoice {0} is not submitted.").format(self.sales_invoice))
		if status not in {"Paid", "Credit Note Issued"}:
			self._block(
				_("Sales Invoice {0} status is {1}; must be Paid.").format(
					self.sales_invoice, status
				)
			)

	def _enforce_top_credit(self, contract):
		"""Block if outstanding > credit_limit, or any overdue invoice exists."""
		outstanding = (
			frappe.db.sql(
				"""
				SELECT COALESCE(SUM(outstanding_amount), 0)
				FROM `tabSales Invoice`
				WHERE customer = %s AND docstatus = 1 AND status != 'Cancelled'
				""",
				(self.customer,),
			)[0][0]
			or 0
		)
		credit_limit = contract.credit_limit or 0
		if credit_limit and outstanding > credit_limit:
			self._block(
				_("TOP credit block: outstanding {0} exceeds credit limit {1}.").format(
					outstanding, credit_limit
				)
			)
		overdue = frappe.db.count(
			"Sales Invoice",
			filters={
				"customer": self.customer,
				"docstatus": 1,
				"status": "Overdue",
			},
		)
		if overdue:
			self._block(
				_("TOP credit block: {0} overdue Sales Invoice(s) for customer.").format(overdue)
			)

	def _block(self, reason: str):
		# Persist outside the about-to-throw transaction so the Blocked status
		# survives the rollback and is visible in audit / portal.
		self.booking_status = "Blocked"
		self.block_reason = reason
		if not self.is_new():
			frappe.db.set_value(
				self.doctype,
				self.name,
				{"booking_status": "Blocked", "block_reason": reason},
				update_modified=False,
			)
			frappe.db.commit()
		frappe.throw(reason)

	def _issue_booking_codes(self):
		issued_at = now_datetime()
		expires_at = add_to_date(issued_at, hours=CODE_TTL_HOURS)
		for item in self.items or []:
			if item.booking_code:
				continue
			code = frappe.get_doc({
				"doctype": "Booking Code",
				"code": generate_code(),
				"booking": self.name,
				"direction": self.direction,
				"container": item.container,
				"container_no": item.container_no or (
					frappe.db.get_value("Container", item.container, "container_no")
					if item.container else None
				),
				"status_tag": item.status_tag or "Dirty",
				"state": "Active",
				"issued_at": issued_at,
				"expires_at": expires_at,
			}).insert(ignore_permissions=True)
			# Persist the back-ref without re-validating the parent.
			frappe.db.set_value(
				"Isotank Booking Item",
				item.name,
				"booking_code",
				code.name,
				update_modified=False,
			)
