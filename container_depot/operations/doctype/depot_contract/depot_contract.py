import frappe
from frappe import _
from frappe.model.document import Document


class DepotContract(Document):
	def validate(self):
		self._validate_date_window()
		self._validate_payment_type()

	def before_save(self):
		# Clear TOP-only fields when payment is Cash
		if self.payment_type == "Cash":
			self.payment_terms = None
			self.credit_limit = 0

	def on_update(self):
		# Auto-expire on date rollover. Idempotent.
		from frappe.utils import getdate, today
		if self.status == "Active" and self.valid_to and getdate(self.valid_to) < getdate(today()):
			self.db_set("status", "Expired", update_modified=False)

	def _validate_date_window(self):
		from frappe.utils import getdate
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To must be on or after Valid From."))

	def _validate_payment_type(self):
		if self.payment_type == "TOP":
			if not self.payment_terms:
				frappe.throw(_("Payment Terms is required for TOP contracts."))
			if not self.credit_limit or self.credit_limit <= 0:
				frappe.throw(_("Credit Limit must be greater than zero for TOP contracts."))
		if self.status == "Active" and not (self.tariff_lines and len(self.tariff_lines) > 0):
			frappe.throw(_("An Active contract must declare at least one Tariff line."))


def get_active_contract(customer: str) -> dict | None:
	"""Return the most recent Active contract for a customer (dict) or None."""
	row = frappe.db.get_value(
		"Depot Contract",
		{"customer": customer, "status": "Active"},
		["name", "payment_type", "payment_terms", "credit_limit", "valid_to"],
		as_dict=True,
		order_by="valid_from desc",
	)
	return row
