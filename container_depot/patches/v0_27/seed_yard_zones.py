"""Depot Storage feature — seed the SOP yard model + legacy-compat zones.

The ``yard_zone`` field on Container / Container Movement moves from a hardcoded
Select to a Link → ``Yard Zone`` master. This patch makes that switch safe and
seeds the physical model from the OAK Isotank workflow SOP:

1. Two NEW depots ``OAK1`` / ``OAK2`` (Depo OAK 1 & 2).
2. SOP zones under them (Blok Kiri/Kanan, cleaning bay, workshop, survey) with the
   stacking limits (5 tiers, 5 rows normal / 6 when full).
3. Legacy-compat zones whose code == the old Select values (``Storage_Yard_A`` …),
   so existing Container/Movement values remain valid Links with no row rewrite.

Idempotent: existing depots/zones are skipped. Runs post_model_sync so the new
``Yard Zone`` DocType + the Link column exist.
"""

from __future__ import annotations

import frappe

DEFAULT_DEPOT_CODE = "SUB"

# (depot_code, depot_name)
NEW_DEPOTS = [
	("OAK1", "Depo OAK 1"),
	("OAK2", "Depo OAK 2"),
]

# (zone_code, zone_name, depot, block, category, capacity)
SOP_ZONES = [
	("OAK1-KIRI-DIRTY", "OAK 1 · Blok Kiri · Antrean Cuci", "OAK1", "Blok Kiri", "Empty Dirty Queue", 60),
	("OAK1-KIRI-READY", "OAK 1 · Blok Kiri · Tank Ready", "OAK1", "Blok Kiri", "Ready", 80),
	("OAK1-KANAN-CLEAN", "OAK 1 · Blok Kanan · Empty Clean Masuk", "OAK1", "Blok Kanan", "Empty Clean", 80),
	("OAK1-KANAN-READY", "OAK 1 · Blok Kanan · Pasca-Cuci (Ready)", "OAK1", "Blok Kanan", "Ready", 80),
	("OAK1-CBAY", "OAK 1 · Cleaning Bay", "OAK1", "", "Cleaning Bay", 15),
	("OAK1-WORKSHOP", "OAK 1 · Workshop", "OAK1", "", "Workshop", 20),
	("OAK1-SURVEY", "OAK 1 · Survey Lane", "OAK1", "", "Survey", 10),
	("OAK2-CLEAN", "OAK 2 · Empty Clean Masuk", "OAK2", "", "Empty Clean", 120),
	("OAK2-READY", "OAK 2 · Tank Ready", "OAK2", "", "Ready", 120),
	("OAK2-SURVEY", "OAK 2 · Survey Lane", "OAK2", "", "Survey", 10),
]

# Legacy Select values -> (category, capacity). Carried forward so pre-existing
# Container.yard_zone / Container Movement.*_zone strings stay valid Links.
LEGACY_ZONES = {
	"Storage_Yard_A": ("Ready", 100),
	"Storage_Yard_B": ("Ready", 80),
	"Cleaning_Bay_C": ("Cleaning Bay", 15),
	"Workshop_D": ("Workshop", 20),
	"Survey_Lane_E": ("Survey", 10),
	"Gate_F": ("Gate", 5),
	"PreClean_Buffer": ("Empty Dirty Queue", 25),
}

STACKING = {"max_rows": 5, "max_rows_full": 6, "max_tiers": 5}


def _ensure_branch():
	"""Resolve a Branch for the new depots (Depot.branch is required)."""
	branch = frappe.db.get_value("Depot", DEFAULT_DEPOT_CODE, "branch")
	if branch:
		return branch
	existing = frappe.get_all("Branch", pluck="name", limit=1)
	if existing:
		return existing[0]
	doc = frappe.get_doc({"doctype": "Branch", "branch": "OAK"}).insert(ignore_permissions=True)
	return doc.name


def _ensure_zone(code, name, depot, block, category, capacity):
	if frappe.db.exists("Yard Zone", code):
		return
	frappe.get_doc({
		"doctype": "Yard Zone",
		"zone_code": code,
		"zone_name": name,
		"depot": depot,
		"block": block or None,
		"category": category,
		"capacity": capacity,
		"is_active": 1,
		**STACKING,
	}).insert(ignore_permissions=True)


def execute():
	branch = _ensure_branch()

	for code, name in NEW_DEPOTS:
		if not frappe.db.exists("Depot", code):
			frappe.get_doc({
				"doctype": "Depot",
				"depot_code": code,
				"depot_name": name,
				"branch": branch,
				"is_active": 1,
			}).insert(ignore_permissions=True)

	for code, name, depot, block, category, capacity in SOP_ZONES:
		_ensure_zone(code, name, depot, block, category, capacity)

	# Legacy zones attach to the original default depot so old data resolves.
	legacy_depot = DEFAULT_DEPOT_CODE if frappe.db.exists("Depot", DEFAULT_DEPOT_CODE) else (
		(frappe.get_all("Depot", pluck="name", limit=1) or [None])[0]
	)
	if legacy_depot:
		for code, (category, capacity) in LEGACY_ZONES.items():
			_ensure_zone(code, code, legacy_depot, "", category, capacity)

	frappe.db.commit()
	print(
		f"[container_depot] seed_yard_zones: ensured {len(NEW_DEPOTS)} depot(s), "
		f"{len(SOP_ZONES)} SOP zone(s), {len(LEGACY_ZONES)} legacy zone(s)."
	)
