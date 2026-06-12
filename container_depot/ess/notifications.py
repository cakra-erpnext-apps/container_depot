"""ESS PWA notification endpoints — the in-app bell reads the caller's own
Notification Log (the same per-user feed Frappe's Desk bell uses). Thin
``@frappe.whitelist`` wrappers; everything is scoped to ``frappe.session.user`` so
no extra DocPerm is needed.
"""

from __future__ import annotations

import frappe
from frappe import _

from container_depot.api import _require_authenticated_user


@frappe.whitelist(methods=["GET"])
def list_notifications(limit=20):
	"""GET /api/method/…list_notifications — the caller's notifications (newest
	first) plus the unread count for the bell badge."""
	_require_authenticated_user()
	user = frappe.session.user
	limit = min(max(int(limit or 20), 1), 50)
	items = frappe.get_all(
		"Notification Log",
		filters={"for_user": user},
		fields=["name", "subject", "document_type", "document_name", "read", "type", "creation"],
		order_by="creation desc",
		limit=limit,
	)
	unread = frappe.db.count("Notification Log", {"for_user": user, "read": 0})
	return {"items": items, "unread": unread}


@frappe.whitelist(methods=["POST"])
def mark_read(name):
	"""POST — mark one of the caller's own notifications as read."""
	_require_authenticated_user()
	if frappe.db.get_value("Notification Log", name, "for_user") != frappe.session.user:
		frappe.throw(_("Not your notification."), frappe.PermissionError)
	frappe.db.set_value("Notification Log", name, "read", 1, update_modified=False)
	return {"name": name, "read": 1}


@frappe.whitelist(methods=["POST"])
def mark_all_read():
	"""POST — mark all of the caller's unread notifications as read."""
	_require_authenticated_user()
	frappe.db.set_value(
		"Notification Log",
		{"for_user": frappe.session.user, "read": 0},
		"read",
		1,
		update_modified=False,
	)
	return {"unread": 0}
