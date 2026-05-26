import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class ContainerMovement(Document):
	def before_insert(self):
		"""Set defaults and capture previous container location/coordinates"""
		if not self.movement_timestamp:
			self.movement_timestamp = now_datetime()
		if not self.moved_by:
			self.moved_by = frappe.session.user or "Administrator"

		if self.container:
			container_doc = frappe.get_doc("Container", self.container)
			self.from_zone = container_doc.yard_zone
			self.from_row = container_doc.row
			self.from_bay = container_doc.bay
			self.from_tier = container_doc.tier

	def after_insert(self):
		"""Update container location and coordinates to destination"""
		if self.container:
			container_doc = frappe.get_doc("Container", self.container)
			container_doc.yard_zone = self.to_zone
			container_doc.current_location = self.to_zone
			container_doc.row = self.to_row
			container_doc.bay = self.to_bay
			container_doc.tier = self.to_tier
			container_doc.save(ignore_permissions=True)
