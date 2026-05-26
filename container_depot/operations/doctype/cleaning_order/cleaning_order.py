import frappe
from frappe.model.document import Document
import datetime
import hashlib

class CleaningOrder(Document):
	def before_insert(self):
		"""Generate cleaning order ID"""
		self.order_id = self.generate_order_id()
		self.order_created = datetime.datetime.now()
		self.created_by = frappe.session.user

	def generate_order_id(self):
		"""Generate unique cleaning order ID"""
		timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		unique = hashlib.md5(f"{timestamp}{frappe.generate_hash()[:10]}".encode()).hexdigest()[:8].upper()
		return f"CO-{unique}"

	def before_save(self):
		"""Auto-populate container info"""
		if self.container:
			container = frappe.get_doc("Container", self.container)
			self.container_no = container.container_no
			self.last_cargo = container.last_cargo
			self.zone = container.yard_zone

	def calculate_priority_score(self):
		"""
		Calculate priority score for cleaning queue.
		Higher score = higher priority.
		"""
		score = 0

		# Factor 1: Release date urgency (if known)
		# This would need integration with release orders

		# Factor 2: Time in queue (older = higher priority)
		if self.order_created:
			hours_in_queue = (datetime.datetime.now() - self.order_created).total_seconds() / 3600
			score += hours_in_queue * 0.5

		# Factor 3: Last cargo type (hazardous = higher priority)
		hazardous_cargos = ["Chemical", "Toxic", "Corrosive", "Flammable"]
		if self.last_cargo:
			for cargo in hazardous_cargos:
				if cargo.lower() in self.last_cargo.lower():
					score += 50
					break

		# Factor 4: Customer tier (premium customers get priority)
		# This would need integration with customer master

		self.priority_score = score
		return score

	def on_submit(self):
		"""Update container status when cleaning order is submitted"""
		if self.container:
			container = frappe.get_doc("Container", self.container)
			if self.status == "In_Progress":
				container.cleaning_status = "In_Progress"
			elif self.status == "Completed":
				container.cleaning_status = "Completed"
				container.status = "Ready_For_Service"
			container.save(ignore_permissions=True)
