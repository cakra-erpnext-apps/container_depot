import frappe
from frappe.model.document import Document
import datetime
import hashlib

class Inspection(Document):
	def before_insert(self):
		"""Generate inspection ID"""
		self.inspection_id = self.generate_inspection_id()

	def generate_inspection_id(self):
		"""Generate unique inspection ID"""
		timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		unique = hashlib.md5(f"{timestamp}{frappe.generate_hash()[:10]}".encode()).hexdigest()[:8].upper()
		return f"EIR-{unique}"

	def before_save(self):
		"""Auto-populate container number"""
		if self.container:
			container = frappe.get_doc("Container", self.container)
			self.container_no = container.container_no

	def validate(self):
		"""Validate inspection data"""
		# Validate that 4 exterior photos are uploaded for EIR-In
		if self.inspection_type == "EIR-In":
			exterior_views = [p.photo_view for p in self.exterior_photos if p.photo_view in ["Front", "Back", "Left", "Right"]]
			if len(exterior_views) < 4:
				frappe.msgprint(f"Warning: Only {len(exterior_views)} exterior photos uploaded. 4 views (Front, Back, Left, Right) recommended for EIR-In.")

	def on_submit(self):
		"""Update container status when inspection is submitted"""
		container = frappe.get_doc("Container", self.container)

		if self.inspection_type == "EIR-In":
			container.status = "Inspecting"
			container.eir_in_date = datetime.datetime.now()
			container.save(ignore_permissions=True)
