"""ISO Tank Cleanliness Statement — the in-house surveyor's cleanliness record.

Mirrors the EIR (Inspection) controller pattern: the rich document carries the
detail; finalize hooks drive the Container and write the append-only audit feed.

On submit a *valid* statement moves the container toward ``Available`` and mints a
no-expiry Cleaning Certificate — the existing TANK OUT gating token — so an
Empty-Dirty tank can leave the depot. Validity is anchored per source EIR (no
time expiry), so the minted certificate carries ``valid_until = None``.
"""

import datetime
import hashlib

import frappe
from frappe.model.document import Document


class CleaningStatement(Document):
	def before_insert(self):
		if not self.statement_id:
			self.statement_id = self.generate_statement_id()
		if not self.date_of_issue:
			self.date_of_issue = frappe.utils.today()
		if not self.signed_by:
			self.signed_by = frappe.session.user or "Administrator"

	def generate_statement_id(self):
		timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		unique = hashlib.md5(f"{timestamp}{frappe.generate_hash()[:10]}".encode()).hexdigest()[:8].upper()
		return f"CLS-{unique}"

	def before_save(self):
		if self.container and not self.container_no:
			self.container_no = frappe.db.get_value("Container", self.container, "container_no")

	def after_insert(self):
		"""Append one Container Activity row when the statement is issued."""
		from container_depot.operations.container_activity import log_container_activity

		log_container_activity(
			self.container, "Cleaning Certificate",
			reference_doctype=self.doctype, reference_name=self.name,
			performed_by=self.get("signed_by"),
			activity_time=self.get("date_of_issue"),
			summary=f"ISO tank cleanliness statement {self.statement_id}"
			+ (f" (EIR {self.inspection})" if self.inspection else ""),
		)

	def on_submit(self):
		"""A valid statement clears the tank: move it toward Available and mint the
		no-expiry Cleaning Certificate the TANK OUT gate checks for."""
		from container_depot.operations.container_activity import log_container_activity

		container = frappe.get_doc("Container", self.container)
		from_status = container.status

		container.status = "Available"
		container.cleaning_status = "Completed"
		container.certification_status = "Completed"
		# Park the tank in the depot's Cleaning Bay zone. Physical yard movement is
		# manual and may lag, so the system stamps the bay here at certification time.
		bay = self._cleaning_bay_zone(container.depot)
		if bay:
			container.yard_zone = bay
		self._save_container(container)

		self._complete_cleaning_order()

		cert = self._mint_cleaning_certificate()
		self.db_set("cleaning_certificate", cert, update_modified=False)

		log_container_activity(
			self.container, "Cleaning",
			reference_doctype=self.doctype, reference_name=self.name,
			from_status=from_status, to_status=container.status,
			performed_by=self.get("signed_by"),
			summary=f"Cleanliness statement submitted — tank cleared (cert {cert})",
		)

	def _save_container(self, container):
		# Controller-driven status change: bypass the manual-transition guard.
		frappe.flags.in_status_automation = True
		try:
			container.save(ignore_permissions=True)
		finally:
			frappe.flags.in_status_automation = False

	def _cleaning_bay_zone(self, depot):
		"""The active Cleaning Bay Yard Zone for the depot (None if none configured)."""
		if not depot:
			return None
		return frappe.db.get_value(
			"Yard Zone", {"depot": depot, "category": "Cleaning Bay", "is_active": 1}, "name"
		)

	def _complete_cleaning_order(self):
		"""Complete the linked Cleaning Order: Completed + submitted (docstatus 1).

		Per the lifecycle — Draft=Pending, In_Progress, Submit=Completed — submitting the
		Cleaning Statement finalizes the order. Permissions are bypassed (the statement is
		the authority); the order's own ``on_submit`` then re-affirms the container."""
		if not self.cleaning_order:
			return
		co = frappe.get_doc("Cleaning Order", self.cleaning_order)
		if co.docstatus == 1 or co.status == "Completed":
			return
		co.status = "Completed"
		co.completed_by = self.signed_by or frappe.session.user
		co.cleaning_end = datetime.datetime.now()
		co.flags.ignore_permissions = True
		co.submit()

	def _mint_cleaning_certificate(self) -> str:
		"""Create + submit a no-expiry Cleaning Certificate from this statement.

		Idempotent: returns the already-minted certificate if present. The cert is the
		gating token consumed by Order Muat / ``_latest_valid_cleaning_cert``; the rich
		cleanliness detail stays on this statement.
		"""
		if self.cleaning_certificate:
			return self.cleaning_certificate
		cert = frappe.new_doc("Cleaning Certificate")
		cert.container = self.container
		cert.clean_date = self.date_of_issue
		cert.cleaning_method = "Steam Wash"
		cert.certified_by = self.signed_by or frappe.session.user
		cert.prior_cargo = self.previous_cargo
		cert.valid_until = None  # no expiry — validity is anchored per EIR
		cert.flags.no_expiry = True
		cert.remarks = (
			f"Auto-issued from Cleaning Statement {self.name}"
			+ (f" (EIR {self.inspection})" if self.inspection else "")
		)
		cert.insert(ignore_permissions=True)
		cert.submit()
		return cert.name
