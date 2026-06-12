"""Tests for document notifications, the Depot PWA role/perms, and the in-PWA
notification bell endpoints."""

import frappe
from frappe.tests.utils import FrappeTestCase

from container_depot.install import (
	PWA_ROLE,
	ROLE_DOCTYPE_PERMISSIONS,
	ensure_roles_exist,
	setup_document_notifications,
)


class TestDocumentNotifications(FrappeTestCase):
	def test_creates_all_notifications_idempotently(self):
		setup_document_notifications()
		specs = [
			("Order Bongkar", "Submit"),
			("Order Muat", "Submit"),
			("Depot Contract", "New"),
			("Container Booking", "Submit"),
			("Inspection", "Submit"),
		]
		for doctype, event in specs:
			self.assertTrue(
				frappe.db.exists(
					"Notification", {"document_type": doctype, "event": event, "is_standard": 0}
				),
				f"missing notification for {doctype}/{event}",
			)
		# Idempotent: a second run adds nothing.
		before = frappe.db.count("Notification", {"is_standard": 0})
		setup_document_notifications()
		self.assertEqual(frappe.db.count("Notification", {"is_standard": 0}), before)


class TestPwaRoleAndPerms(FrappeTestCase):
	def test_pwa_role_created(self):
		ensure_roles_exist()
		self.assertTrue(frappe.db.exists("Role", PWA_ROLE))

	def test_pwa_matrix_grants_pwa_menu_perms(self):
		# The injection loop must have put Depot PWA into the permission matrix.
		self.assertEqual(ROLE_DOCTYPE_PERMISSIONS["Inspection"][PWA_ROLE].get("create"), 1)
		self.assertEqual(ROLE_DOCTYPE_PERMISSIONS["Inspection"][PWA_ROLE].get("submit"), 1)
		self.assertEqual(ROLE_DOCTYPE_PERMISSIONS["Container"][PWA_ROLE].get("read"), 1)
		self.assertEqual(ROLE_DOCTYPE_PERMISSIONS["Order Bongkar"][PWA_ROLE].get("read"), 1)


class TestPwaNotificationEndpoints(FrappeTestCase):
	def test_list_and_mark_read(self):
		from container_depot.ess import notifications

		log = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": "Test EIR notif",
				"for_user": frappe.session.user,
				"type": "Alert",
				"read": 0,
			}
		).insert(ignore_permissions=True)

		res = notifications.list_notifications(limit=20)
		self.assertIn(log.name, [i["name"] for i in res["items"]])
		self.assertGreaterEqual(res["unread"], 1)

		notifications.mark_read(log.name)
		self.assertEqual(frappe.db.get_value("Notification Log", log.name, "read"), 1)

	def test_mark_all_read(self):
		from container_depot.ess import notifications

		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": "Another notif",
				"for_user": frappe.session.user,
				"type": "Alert",
				"read": 0,
			}
		).insert(ignore_permissions=True)

		notifications.mark_all_read()
		self.assertEqual(
			frappe.db.count("Notification Log", {"for_user": frappe.session.user, "read": 0}), 0
		)
