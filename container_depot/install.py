import frappe

ROLES_TO_GRANT = ["System Manager", "Container Depot"]


def after_install():
	"""Run after install hook for container_depot app"""
	ensure_roles_exist()
	setup_permissions()
	setup_workspace()


def ensure_roles_exist():
	"""Create app-specific roles referenced by setup_permissions if missing."""
	for role_name in ROLES_TO_GRANT:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}).insert(ignore_permissions=True)
	frappe.db.commit()


def setup_permissions():
	"""Grant Operations DocType permissions to every role in ROLES_TO_GRANT."""
	doctypes = [d.name for d in frappe.get_all("DocType", filters={"module": "Operations"})]
	for dt in doctypes:
		meta = frappe.get_meta(dt)
		for role_name in ROLES_TO_GRANT:
			if frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role_name}):
				continue
			frappe.get_doc({
				"doctype": "Custom DocPerm",
				"parent": dt,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": role_name,
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
				"report": 1,
			}).insert(ignore_permissions=True)
	frappe.db.commit()


def setup_workspace():
	"""Pin Container Depot workspace to the top of the sidebar."""
	if frappe.db.exists("Workspace", "Container Depot"):
		frappe.db.set_value("Workspace", "Container Depot", "sequence_id", 0)
		frappe.db.set_value("Workspace", "Container Depot", "parent_page", "")
		frappe.db.commit()
