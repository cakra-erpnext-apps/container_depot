"""The desk app-switcher (bootinfo.app_data) must hide apps a restricted user has
no visible workspaces for. Regression test for the extend_bootinfo prune hook."""

import frappe
from frappe.tests.utils import FrappeTestCase

from container_depot.boot import prune_app_switcher


def _boot(*apps):
	"""Fake bootinfo. apps = (app_name, [visible workspaces]) tuples."""
	return frappe._dict(app_data=[{"app_name": a, "workspaces": list(ws)} for a, ws in apps])


class TestAppSwitcherPrune(FrappeTestCase):
	def test_admin_keeps_every_app(self):
		# Tests run as Administrator (System/Workspace Manager) -> never trimmed.
		bi = _boot(("frappe", []), ("container_depot", ["Container Depot"]))
		prune_app_switcher(bi)
		self.assertEqual([a["app_name"] for a in bi.app_data], ["frappe", "container_depot"])

	def test_restricted_user_loses_workspaceless_apps(self):
		email = "switcher-prune@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Switcher",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			bi = _boot(("frappe", []), ("hrms", []), ("container_depot", ["Container Depot"]))
			prune_app_switcher(bi)
			# Only the app with a visible workspace survives.
			self.assertEqual([a["app_name"] for a in bi.app_data], ["container_depot"])
		finally:
			frappe.set_user("Administrator")

	def test_noop_when_no_app_data(self):
		bi = frappe._dict()
		prune_app_switcher(bi)  # must not raise
		self.assertIsNone(bi.get("app_data"))
