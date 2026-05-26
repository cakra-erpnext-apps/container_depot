import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "name",
			"label": "Gasket ID",
			"fieldtype": "Link",
			"options": "Gasket Inventory",
			"width": 120
		},
		{
			"fieldname": "gasket_name",
			"label": "Gasket Name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "type",
			"label": "Type",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "current_stock",
			"label": "Current Stock",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "reorder_point",
			"label": "Reorder Point",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": "Stock Status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "unit_price",
			"label": "Unit Price",
			"fieldtype": "Currency",
			"width": 100
		}
	]

def get_data(filters):
	query_filters = {}
	if filters and filters.get("type"):
		query_filters["type"] = filters.get("type")

	items = frappe.get_all(
		"Gasket Inventory",
		filters=query_filters,
		fields=["name", "gasket_name", "type", "current_stock", "reorder_point", "unit_price"]
	)

	for item in items:
		if item.current_stock <= item.reorder_point:
			item.status = "Low Stock"
		else:
			item.status = "Healthy"

	return items
