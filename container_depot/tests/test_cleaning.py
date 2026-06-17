"""ISO Tank Cleanliness Statement (operations.cleaning + Cleaning Statement doctype).

Covers: the seeded 12-row checklist (idempotent), prefill from the Container master,
create + submit (which moves the container toward Available and mints a no-expiry
Cleaning Certificate the TANK OUT gate accepts), the after_insert activity log, and
that the minted certificate satisfies ``_latest_valid_cleaning_cert``.

Cleaning Statement submit drives the container + mints a certificate, so created docs
are removed explicitly after each test.
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from container_depot.api import _latest_valid_cleaning_cert
from container_depot.operations import cleaning
from container_depot.patches.v0_31 import seed_cleaning_checklist
from container_depot.tests.test_eir import _make_container


class TestCleaningStatement(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		seed_cleaning_checklist.execute()  # ensure the 12-row master exists
		self._containers = []
		self._statements = []

	def tearDown(self):
		for s in self._statements:
			cert = frappe.db.get_value("Cleaning Statement", s, "cleaning_certificate")
			if cert:
				frappe.db.delete("Cleaning Certificate", {"name": cert})
			frappe.db.delete("Cleaning Statement", {"name": s})
		for c in self._containers:
			frappe.db.delete("Cleaning Certificate", {"container": c})
			frappe.db.delete("Cleaning Statement", {"container": c})
			frappe.db.delete("Container Activity", {"container": c})
			frappe.db.delete("Container", {"name": c})
		frappe.db.commit()
		super().tearDown()

	def _container(self, cno, **kw):
		c = _make_container(cno, **kw)
		self._containers.append(c)
		return c

	def _create(self, container, *, submit=False, results=None, **kw):
		res = cleaning.create_cleaning_statement(container=container, submit=submit, results=results, **kw)
		self._statements.append(res["name"])
		return res

	# --- seed / masters -------------------------------------------------------
	def test_seed_is_idempotent_12_rows(self):
		before = frappe.db.count("Cleaning Checklist Item")
		seed_cleaning_checklist.execute()  # re-run
		after = frappe.db.count("Cleaning Checklist Item")
		self.assertEqual(before, after)  # no duplicates
		masters = cleaning.get_cleaning_masters()
		self.assertEqual(len(masters["checklist"]), 12)
		sections = {r["section"] for r in masters["checklist"]}
		self.assertEqual(sections, {"Exterior", "Interior", "Valves & Fittings"})

	# --- prefill --------------------------------------------------------------
	def test_prefill_returns_container_master_fields(self):
		from frappe.utils import today

		c = self._container(
			"CLNPREF0001",
			container_type="ISO Tank", tare_weight=3800, max_gross_weight=36000, capacity=26000,
		)
		pf = cleaning.prefill(container=c)
		self.assertEqual(pf["container"], c)
		self.assertEqual(pf["tank_type"], "ISO Tank")
		self.assertEqual(pf["tare"], 3800)
		self.assertEqual(pf["mgw"], 36000)
		self.assertEqual(pf["capacity"], 26000)
		self.assertEqual(str(pf["date_of_issue"]), today())
		self.assertEqual(pf["signed_by"], "Administrator")

	# --- create + submit ------------------------------------------------------
	def test_create_records_all_12_checklist_rows(self):
		c = self._container("CLNROWS0001")
		res = self._create(c, results=[{"item_code": "06", "result": "No", "note": "slight odour"}])
		doc = frappe.get_doc("Cleaning Statement", res["name"])
		self.assertEqual(len(doc.checklist), 12)
		odour = next(r for r in doc.checklist if r.checklist_item == "06")
		self.assertEqual(odour.result, "No")
		self.assertEqual(odour.note, "slight odour")
		# Unspecified items default to Yes.
		self.assertTrue(all(r.result in ("Yes", "No") for r in doc.checklist))

	def test_submit_moves_container_and_mints_no_expiry_cert(self):
		c = self._container("CLNSUBM0001", status="Cleaning_In_Progress")
		res = self._create(c, submit=True)
		self.assertEqual(res["docstatus"], 1)

		container = frappe.get_doc("Container", c)
		self.assertEqual(container.status, "Available")
		self.assertEqual(container.cleaning_status, "Completed")

		cert = res["cleaning_certificate"]
		self.assertTrue(cert)
		cert_doc = frappe.db.get_value(
			"Cleaning Certificate", cert, ["container", "valid_until", "docstatus"], as_dict=True
		)
		self.assertEqual(cert_doc.container, c)
		self.assertEqual(cert_doc.docstatus, 1)
		self.assertIsNone(cert_doc.valid_until)  # no expiry — validity anchored per EIR

	def test_minted_cert_satisfies_tank_out_gating(self):
		c = self._container("CLNGATE0001", status="Cleaning_In_Progress")
		res = self._create(c, submit=True)
		self.assertEqual(_latest_valid_cleaning_cert(c), res["cleaning_certificate"])

	def test_after_insert_logs_container_activity(self):
		c = self._container("CLNACTV0001")
		res = self._create(c, submit=False)  # draft only
		acts = frappe.get_all(
			"Container Activity",
			filters={"container": c, "reference_doctype": "Cleaning Statement", "reference_name": res["name"]},
			pluck="activity_type",
		)
		self.assertEqual(len(acts), 1)
		self.assertEqual(acts[0], "Cleaning Certificate")
