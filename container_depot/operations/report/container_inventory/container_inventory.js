// Container Inventory — live per-tank monitoring list. Defaults to tanks
// physically in the depo; toggle "In Depo Only" off to include reserved /
// gated-out tanks.
frappe.query_reports["Container Inventory"] = {
	filters: [
		{
			fieldname: "principal",
			label: __("Principal"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "depot",
			label: __("Depot"),
			fieldtype: "Link",
			options: "Depot",
		},
		{
			fieldname: "inventory_stage",
			label: __("Inventory Stage"),
			fieldtype: "Select",
			options: "\nPre-Arrival\nIncoming\nCleaning\nSurvey\nRepair (M&R)\nReady\nOutgoing\nDeparted",
		},
		{
			fieldname: "yard_zone",
			label: __("Yard Zone"),
			fieldtype: "Select",
			options: "\nStorage_Yard_A\nStorage_Yard_B\nCleaning_Bay_C\nWorkshop_D\nSurvey_Lane_E\nGate_F\nPreClean_Buffer",
		},
		{
			fieldname: "in_depo_only",
			label: __("In Depo Only"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
