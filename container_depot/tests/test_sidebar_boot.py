"""Regression test for the desk-boot SessionBootFailed crash.

Frappe's WorkspaceSidebar reads the domain-restricted caches without a lazy-build
fallback; when they are empty (post cache-clear) and the user has no allowed
workspaces, is_item_allowed() does `name in None` and the boot dies. We warm the
caches in a before_request hook so they are never None.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from container_depot.boot import warm_domain_restricted_caches


class TestDomainCacheWarm(FrappeTestCase):
	def test_warm_populates_both_caches(self):
		frappe.cache.delete_value("domain_restricted_pages")
		frappe.cache.delete_value("domain_restricted_doctypes")
		warm_domain_restricted_caches()
		self.assertIsNotNone(frappe.cache.get_value("domain_restricted_pages"))
		self.assertIsNotNone(frappe.cache.get_value("domain_restricted_doctypes"))

	def test_workspace_sidebar_restricted_pages_not_none_after_warm(self):
		names = frappe.get_all("Workspace Sidebar", limit=1, pluck="name")
		if not names:
			self.skipTest("no Workspace Sidebar docs on this site")

		# The crash condition: cache empty -> WorkspaceSidebar.restricted_pages is None.
		frappe.cache.delete_value("domain_restricted_pages")
		self.assertIsNone(frappe.get_doc("Workspace Sidebar", names[0]).restricted_pages)

		# After warming, a freshly loaded sidebar sees a real list (no boot crash).
		warm_domain_restricted_caches()
		self.assertIsNotNone(frappe.get_doc("Workspace Sidebar", names[0]).restricted_pages)
