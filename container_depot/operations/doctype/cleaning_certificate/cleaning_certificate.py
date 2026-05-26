import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class CleaningCertificate(Document):
	def before_insert(self):
		"""Auto-populate fields before insertion"""
		if not self.clean_date:
			self.clean_date = now_datetime()
		if not self.certified_by:
			self.certified_by = frappe.session.user or "Administrator"

		if self.container and not self.prior_cargo:
			self.prior_cargo = frappe.db.get_value("Container", self.container, "last_cargo")

	def on_submit(self):
		"""Update container certification status upon submission"""
		if self.container:
			container_doc = frappe.get_doc("Container", self.container)
			container_doc.certification_status = "Completed"
			container_doc.save(ignore_permissions=True)
