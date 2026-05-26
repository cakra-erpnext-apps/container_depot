import frappe
from frappe.model.document import Document

class FuelLog(Document):
	def before_save(self):
		self.calculate_total_cost()

	def calculate_total_cost(self):
		liters = float(self.liters or 0.0)
		cost_per_liter = float(self.cost_per_liter or 0.0)
		self.total_cost = liters * cost_per_liter
