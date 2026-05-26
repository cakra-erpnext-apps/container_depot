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
			"fieldtype": "Data",
			"width": 150
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
	# Pre-defined zone capacities
	capacities = {
		"Storage_Yard_A": 100,
		"Storage_Yard_B": 80,
		"Cleaning_Bay_C": 15,
		"Workshop_D": 20,
		"Survey_Lane_E": 10,
		"Gate_F": 5,
		"PreClean_Buffer": 25
	}

	# Count containers per zone
	counts = frappe.db.sql("""
		SELECT yard_zone, COUNT(*) as count 
		FROM `tabContainer` 
		WHERE yard_zone IS NOT NULL AND status != 'Gate_Out'
		GROUP BY yard_zone
	""", as_dict=True)

	counts_dict = {r.yard_zone: r.count for r in counts if r.yard_zone}

	data = []
	for zone, capacity in capacities.items():
		count = counts_dict.get(zone, 0)
		util = (count / capacity) * 100 if capacity > 0 else 0
		data.append({
			"yard_zone": zone,
			"container_count": count,
			"suggested_capacity": capacity,
			"utilization": round(util, 2)
		})

	return data
