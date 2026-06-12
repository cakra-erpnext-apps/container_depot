import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "yard_zone",
			"label": "Yard Zone",
			"fieldtype": "Link",
			"options": "Yard Zone",
			"width": 220
		},
		{
			"fieldname": "container_count",
			"label": "Containers Stacked",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "suggested_capacity",
			"label": "Capacity Limit",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "utilization",
			"label": "Utilization (%)",
			"fieldtype": "Percent",
			"width": 120
		}
	]


def get_data(filters):
	# Zone capacities now live on the Yard Zone master (seeded per the OAK SOP),
	# not a hardcoded dict — keeps the report in step with the PWA storage view.
	zones = frappe.get_all(
		"Yard Zone",
		filters={"is_active": 1},
		fields=["name", "capacity"],
		order_by="depot asc, name asc",
	)

	# Count containers per zone (exclude tanks that have left the yard).
	counts = frappe.db.sql("""
		SELECT yard_zone, COUNT(*) as count
		FROM `tabContainer`
		WHERE yard_zone IS NOT NULL AND status != 'Gate_Out'
		GROUP BY yard_zone
	""", as_dict=True)

	counts_dict = {r.yard_zone: r.count for r in counts if r.yard_zone}

	data = []
	for zone in zones:
		capacity = zone.capacity or 0
		count = counts_dict.get(zone.name, 0)
		util = (count / capacity) * 100 if capacity > 0 else 0
		data.append({
			"yard_zone": zone.name,
			"container_count": count,
			"suggested_capacity": capacity,
			"utilization": round(util, 2)
		})

	return data
