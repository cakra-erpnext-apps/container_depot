import frappe
from frappe.model.document import Document

class Container(Document):
	def validate(self):
		"""Validate container number format (ISO 11-character standard)"""
		if self.container_no:
			# ISO container format: 4 letters + 6 digits + 1 check digit
			cleaned = self.container_no.replace("-", "").replace(" ", "").upper()
			if len(cleaned) != 11:
				frappe.throw(f"Container number must be 11 characters (ISO format). Got: {len(cleaned)}")

	def before_save(self):
		"""Auto-format container number"""
		if self.container_no:
			self.container_no = self.container_no.upper()
