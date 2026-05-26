import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today, add_days

class GasketInventory(Document):
	def validate(self):
		"""Check if stock is below reorder point"""
		if self.current_stock <= self.reorder_point:
			frappe.msgprint(f"Alert: {self.gasket_name} stock ({self.current_stock}) is at or below reorder point ({self.reorder_point}).")

	def on_update(self):
		"""Create alert and material request if stock is low"""
		if self.current_stock <= self.reorder_point:
			self.create_low_stock_alert()
			self.create_material_request()

	def create_low_stock_alert(self):
		"""Create a notification for low stock"""
		if not frappe.db.exists("ToDo", {
			"reference_type": self.doctype,
			"reference_name": self.name,
			"status": "Open"
		}):
			frappe.get_doc({
				"doctype": "ToDo",
				"description": f"Low stock alert for {self.gasket_name}. Current: {self.current_stock}, Reorder Point: {self.reorder_point}",
				"reference_type": self.doctype,
				"reference_name": self.name,
				"assigned_by": frappe.session.user or "Administrator",
				"priority": "High"
			}).insert(ignore_permissions=True)

	def create_material_request(self):
		"""Create a standard ERPNext Material Request if not already created"""
		item_code = f"GASKET-{self.gasket_name.replace(' ', '-').upper()}"
		
		# Check if we already have an open Material Request for this item
		if frappe.db.sql("""
			SELECT parent FROM `tabMaterial Request Item` 
			WHERE item_code = %s AND docstatus < 2
		""", (item_code,)):
			return # Already exists and not cancelled

		# Ensure default Item Group exists
		item_group = "All Item Groups"
		if not frappe.db.exists("Item Group", item_group):
			frappe.get_doc({
				"doctype": "Item Group",
				"item_group_name": item_group,
				"is_group": 0,
				"parent_item_group": ""
			}).insert(ignore_permissions=True)

		# Ensure default UOM exists
		if not frappe.db.exists("UOM", "Nos"):
			frappe.get_doc({
				"doctype": "UOM",
				"uom_name": "Nos"
			}).insert(ignore_permissions=True)

		# Ensure Item exists
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": self.gasket_name,
				"item_group": item_group,
				"stock_uom": "Nos",
				"is_stock_item": 1
			}).insert(ignore_permissions=True)

		# Find a Company
		company = frappe.db.get_single_value('Global Defaults', 'default_company') or frappe.db.get_value('Company', {}, 'name')
		warehouse = None
		if company:
			warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
		if not warehouse:
			warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")

		# Create Material Request
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"transaction_date": today(),
			"schedule_date": add_days(today(), 7),
			"company": company,
			"items": [
				{
					"item_code": item_code,
					"qty": self.reorder_point * 2 if self.reorder_point > 0 else 10,
					"uom": "Nos",
					"schedule_date": add_days(today(), 7),
					"warehouse": warehouse
				}
			]
		})
		mr.insert(ignore_permissions=True)
