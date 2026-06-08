"""Container Leasing — lessee/period/status registry (PRD v0.2 §5).

A standalone activity separate from the Tank In/Out booking spine: it records
who is leasing a tank, for which period, the current status and a lifecycle
history. v1 is registry-only — no Sales Invoice automation (that can layer on
ERPNext billing later).
"""

from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import getdate, today


class ContainerLeasing(Document):
	def validate(self):
		self._flag_overdue()

	def _flag_overdue(self):
		"""An Active lease past its end date is Overdue (until explicitly Returned)."""
		if self.status == "Active" and self.lease_end and getdate(self.lease_end) < getdate(today()):
			self.status = "Overdue"
