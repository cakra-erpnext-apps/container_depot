"""Demo data for clicking through the ESS PWA (F1) on a live site.

Namespaced so it's easy to remove:
  seed  -> bench --site <site> execute container_depot.tests._ess_demo_seed.seed
  clear -> bench --site <site> execute container_depot.tests._ess_demo_seed.clear

Not part of the test suite or the app's install — a throwaway helper.
"""

import frappe
from frappe.utils import add_days, today

DEPOT = "DEMO"
# container_no -> raw Container.status (must be 11 ISO chars: DEMU + 7 digits)
TANKS = {
	"DEMU1000001": ("Available", "Stolt"),
	"DEMU1000002": ("Available", "Stolt"),
	"DEMU1000003": ("Gate_Out", "Nichicon"),
	"DEMU1000004": ("Ready_For_Release", "Bertschi"),
	"DEMU1000005": ("Available", "Bertschi"),  # -> cleaning (open CO)
	"DEMU1000006": ("In_Workshop", "NCS"),  # -> repair_survey (dup raw value)
	"DEMU1000007": ("Available", "NCS"),  # -> repair_survey (open RO)
	"DEMU1000008": ("Available", "Stolt"),  # -> repair_survey (open EIR)
}


def _customer(name):
	if frappe.db.exists("Customer", name):
		return name
	return frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_type": "Company",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
			"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"),
		}
	).insert(ignore_permissions=True).name


def seed():
	if not frappe.db.exists("Depot", DEPOT):
		frappe.get_doc(
			{"doctype": "Depot", "depot_code": DEPOT, "depot_name": "Demo Depot (KIM)", "city": "Cikarang"}
		).insert(ignore_permissions=True)

	zones = ["Storage_Yard_A", "Storage_Yard_B", "Cleaning_Bay_C", "Workshop_D"]
	for i, (no, (status, principal)) in enumerate(TANKS.items()):
		if frappe.db.exists("Container", no):
			continue
		frappe.get_doc(
			{
				"doctype": "Container",
				"container_no": no,
				"container_type": "ISO Tank",
				"size": "20'",
				"status": status,
				"principal": _customer(principal),
				"depot": DEPOT,
				"yard_zone": zones[i % len(zones)],
				"capacity": 26000 + i * 100,
				"tare_weight": 3600 + i * 10,
				"max_gross_weight": 36000,
				"last_cargo": ["Methanol", "Ethanol", "Acetic Acid", "Glycol"][i % 4],
				"last_test_date": add_days(today(), -400),
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Cleaning Order", {"container": "DEMU1000005", "status": "Pending"}):
		frappe.get_doc(
			{"doctype": "Cleaning Order", "container": "DEMU1000005", "status": "Pending"}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Repair Order", {"container": "DEMU1000007"}):
		frappe.get_doc(
			{
				"doctype": "Repair Order",
				"container": "DEMU1000007",
				"status": "Draft",
				"billing_status": "Unbilled",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Inspection", {"container": "DEMU1000008", "status": "Submitted"}):
		frappe.get_doc(
			{
				"doctype": "Inspection",
				"container": "DEMU1000008",
				"inspection_type": "EIR-In",
				"status": "Submitted",
				"inspector": "Administrator",
			}
		).insert(ignore_permissions=True)
	# Two periodic tests due soon -> periodic_test_due count = 2.
	for no in ["DEMU1000001", "DEMU1000004"]:
		if not frappe.db.exists("Periodic Test", {"container": no, "status": ["!=", "Completed"]}):
			frappe.get_doc(
				{
					"doctype": "Periodic Test",
					"container": no,
					"status": "Scheduled",
					"test_type": "2,5Y",
					"due_date": add_days(today(), 10),
				}
			).insert(ignore_permissions=True)

	frappe.db.commit()
	print("SEEDED", {"depot": DEPOT, "containers": list(TANKS.keys())})


def clear():
	names = list(TANKS.keys())
	for dt in ["Container Movement", "Cleaning Order", "Repair Order", "Inspection", "Periodic Test"]:
		frappe.db.delete(dt, {"container": ["in", names]})
	frappe.db.delete("Container", {"name": ["in", names]})
	if frappe.db.exists("Depot", DEPOT):
		frappe.db.delete("Depot", {"name": DEPOT})
	frappe.db.commit()
	print("CLEARED", {"depot": DEPOT, "containers": names})
