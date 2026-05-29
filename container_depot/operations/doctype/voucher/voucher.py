"""DEPRECATED — replaced by Isotank Booking + Booking Code.

This module is kept on the import path so existing data can still be read and
historical reports keep working. The doctype is hidden from the workspace as
of Phase 5b. A follow-up commit (Phase 5b-drop) will physically remove the
DocType directory once the operator has confirmed there are no remaining
production sites that need to read these rows.
"""

import datetime
import hashlib

import frappe
from frappe.model.document import Document


class Voucher(Document):
	def before_insert(self):
		"""Generate voucher ID and QR code data"""
		if not self.voucher_id:
			self.voucher_id = self.generate_voucher_id()
		if not self.qr_code:
			self.qr_code = self.generate_qr_data()

	def generate_voucher_id(self):
		"""Generate unique voucher ID"""
		timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		unique = hashlib.md5(f"{timestamp}{frappe.generate_hash()[:10]}".encode()).hexdigest()[:8].upper()
		return f"VOUCH-{unique}"

	def generate_qr_data(self):
		"""Generate QR code content (can be used to generate actual QR image)"""
		qr_content = f"OAK|{self.voucher_id}|{self.voucher_type}|{self.client}"
		return qr_content

	def validate(self):
		"""Validate voucher before save"""
		if self.voucher_type == "Gate_In (Bon Bongkar)":
			if not self.expected_containers:
				frappe.throw("At least one container must be specified for Gate-In voucher")

	def on_submit(self):
		"""Mark payment as verified if submitted"""
		if self.payment_status:
			self.payment_verified_at = datetime.datetime.now()

	def get_pending_containers(self):
		"""Return containers that haven't been processed yet"""
		return [c for c in self.expected_containers if c.status not in ["Gate_Out", "Completed"]]
