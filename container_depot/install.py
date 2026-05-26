import frappe

def after_install():
	"""Run after install hook for container_depot app"""
	setup_permissions()
	setup_workspace()

def setup_permissions():
	"""Create default permissions for Operations custom doctypes"""
	doctypes = [d.name for d in frappe.get_all("DocType", filters={"module": "Operations"})]
	for dt in doctypes:
		if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": "System Manager"}):
			meta = frappe.get_meta(dt)
			doc = frappe.get_doc({
				"doctype": "Custom DocPerm",
				"parent": dt,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": "System Manager",
				"permlevel": 0,
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 1 if meta.is_submittable else 0,
				"cancel": 1 if meta.is_submittable else 0,
				"amend": 1 if meta.is_submittable else 0,
				"export": 1,
				"import": 1,
				"share": 1,
				"report": 1
			})
			doc.insert(ignore_permissions=True)
	frappe.db.commit()

def setup_workspace():
	"""Set Container Depot workspace to the top of the sidebar (sequence_id = 0) and remove parent page"""
	if frappe.db.exists("Workspace", "Container Depot"):
		frappe.db.set_value("Workspace", "Container Depot", "sequence_id", 0)
		frappe.db.set_value("Workspace", "Container Depot", "parent_page", "")
		frappe.db.commit()


