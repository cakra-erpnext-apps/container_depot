import frappe
from frappe.model.document import Document


class YardZone(Document):
	def validate(self):
		"""Keep the SOP stacking numbers internally consistent."""
		for field in ("capacity", "max_rows", "max_rows_full", "max_tiers"):
			if (self.get(field) or 0) < 0:
				frappe.throw(frappe._("{0} cannot be negative.").format(self.meta.get_label(field)))
		if (self.max_rows or 0) and (self.max_rows_full or 0) and self.max_rows_full < self.max_rows:
			frappe.throw(frappe._("Max Rows (full) must be greater than or equal to Max Rows (normal)."))
