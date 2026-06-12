"""Sync a User's selected depot Branches into Frappe User Permissions.

The User doctype carries a `branch` Table MultiSelect (child: "Allowed Branch").
We mirror those picks into native **User Permission** rows on "Branch" so data is
scoped per branch with zero per-doctype code:

- empty selection  -> no Branch User Permissions -> user sees every branch
- one / many picks -> one User Permission per branch (apply_to_all_doctypes) ->
  the user only sees rows whose Branch is in the set (Frappe's native filtering),
  i.e. Container Booking, Order Bongkar/Muat, Sales Invoice, etc.

Wired from hooks `doc_events["User"]["on_update"]`, so it re-syncs on every save.
"""

import frappe

# These accounts must never be branch-restricted (avoids locking admins out).
_SKIP_USERS = {"Administrator", "Guest"}


def sync_user_branch_permissions(doc, method=None):
	"""Reconcile (user, allow=Branch) User Permission rows to match the User's
	`branch` multiselect. Idempotent: only inserts the missing ones and deletes
	the de-selected ones."""
	user = doc.name
	if user in _SKIP_USERS:
		return

	desired = {row.branch for row in (doc.get("branch") or []) if row.get("branch")}

	existing = {
		p.for_value: p.name
		for p in frappe.get_all(
			"User Permission",
			filters={"user": user, "allow": "Branch"},
			fields=["name", "for_value"],
		)
	}

	for branch in desired - set(existing):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Branch",
				"for_value": branch,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)

	for branch, name in existing.items():
		if branch not in desired:
			frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)
