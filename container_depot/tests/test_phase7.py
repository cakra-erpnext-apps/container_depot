"""Phase 7 tests — SST stale-heartbeat job + daily ops report execute."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from container_depot.operations.report.daily_operations_report.daily_operations_report import (
	execute as run_daily_report,
)
from container_depot.tasks import mark_stale_sst_heartbeats
from container_depot.tests.test_api import ensure_test_customer


P7_TERMINAL_STALE = "SST-P7-STALE"
P7_TERMINAL_FRESH = "SST-P7-FRESH"
P7_SUPERVISOR = "p7-supervisor@example.com"


class TestSSTStaleHeartbeat(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Supervisor user holding the Ops Supervisor role.
		if not frappe.db.exists("User", P7_SUPERVISOR):
			frappe.get_doc({
				"doctype": "User",
				"email": P7_SUPERVISOR,
				"first_name": "P7",
				"last_name": "Supervisor",
				"send_welcome_email": 0,
				"roles": [{"role": "Ops Supervisor"}],
			}).insert(ignore_permissions=True)
		# Stale terminal — last heartbeat 30 minutes ago.
		if not frappe.db.exists("Self Service Terminal", P7_TERMINAL_STALE):
			frappe.get_doc({
				"doctype": "Self Service Terminal",
				"terminal_id": P7_TERMINAL_STALE,
				"printer_status": "OK",
				"last_heartbeat": add_to_date(now_datetime(), minutes=-30),
			}).insert(ignore_permissions=True)
		# Fresh terminal — just heartbeated.
		if not frappe.db.exists("Self Service Terminal", P7_TERMINAL_FRESH):
			frappe.get_doc({
				"doctype": "Self Service Terminal",
				"terminal_id": P7_TERMINAL_FRESH,
				"printer_status": "OK",
				"last_heartbeat": now_datetime(),
			}).insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("ToDo", {"reference_type": "Self Service Terminal"})
		for t in (P7_TERMINAL_STALE, P7_TERMINAL_FRESH):
			frappe.db.delete("Self Service Terminal", {"terminal_id": t})
		frappe.db.delete("User", {"email": P7_SUPERVISOR})
		frappe.db.commit()
		super().tearDownClass()

	def test_stale_terminal_marked_and_todo_created(self):
		# Make sure starting state is OK for the stale terminal.
		frappe.db.set_value(
			"Self Service Terminal", P7_TERMINAL_STALE, "printer_status", "OK", update_modified=False
		)
		frappe.db.delete("ToDo", {"reference_type": "Self Service Terminal", "reference_name": P7_TERMINAL_STALE})
		marked = mark_stale_sst_heartbeats()
		self.assertGreaterEqual(marked, 1)
		self.assertEqual(
			frappe.db.get_value("Self Service Terminal", P7_TERMINAL_STALE, "printer_status"),
			"Stale",
		)
		todos = frappe.db.count(
			"ToDo",
			{
				"reference_type": "Self Service Terminal",
				"reference_name": P7_TERMINAL_STALE,
				"allocated_to": P7_SUPERVISOR,
				"status": "Open",
			},
		)
		self.assertEqual(todos, 1)

	def test_fresh_terminal_not_marked(self):
		frappe.db.set_value(
			"Self Service Terminal", P7_TERMINAL_FRESH, "printer_status", "OK", update_modified=False
		)
		mark_stale_sst_heartbeats()
		self.assertEqual(
			frappe.db.get_value("Self Service Terminal", P7_TERMINAL_FRESH, "printer_status"),
			"OK",
		)

	def test_no_duplicate_todo_on_second_run(self):
		# Make stale + mark, then mark again; only one open ToDo per user.
		frappe.db.set_value(
			"Self Service Terminal", P7_TERMINAL_STALE, "printer_status", "OK", update_modified=False
		)
		frappe.db.delete("ToDo", {"reference_type": "Self Service Terminal", "reference_name": P7_TERMINAL_STALE})
		mark_stale_sst_heartbeats()
		# Refresh the stale flag back to OK so the row gets re-marked again.
		frappe.db.set_value(
			"Self Service Terminal", P7_TERMINAL_STALE, "printer_status", "OK", update_modified=False
		)
		mark_stale_sst_heartbeats()
		todos = frappe.db.count(
			"ToDo",
			{
				"reference_type": "Self Service Terminal",
				"reference_name": P7_TERMINAL_STALE,
				"allocated_to": P7_SUPERVISOR,
				"status": "Open",
			},
		)
		self.assertEqual(todos, 1)


class TestDailyOperationsReport(FrappeTestCase):
	def test_report_returns_columns_and_rows(self):
		columns, data = run_daily_report()
		self.assertEqual(columns[0]["fieldname"], "section")
		# Always at least the separator rows.
		self.assertGreater(len(data), 3)
		self.assertTrue(any(r.get("metric", "").startswith("── ") for r in data))
