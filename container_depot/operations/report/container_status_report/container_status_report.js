frappe.query_reports["Container Status Report"] = {
	"filters": [
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nAvailable\nGate_In\nInspecting\nNeeds_Cleaning\nNeeds_Repair\nIn_Workshop\nPending_Repair\nPending_Survey\nPending_Cleaning\nCleaning_In_Progress\nRepair_In_Progress\nSurvey_In_Progress\nReady_For_Service\nReady_For_Release\nGate_Out"
		},
		{
			"fieldname": "container_type",
			"label": __("Container Type"),
			"fieldtype": "Select",
			"options": "\nISO Tank\n20ft Dry\n40ft HC\n20ft Reefer\n40ft Reefer\nOpen Top\nFlat Rack"
		},
		{
			"fieldname": "yard_zone",
			"label": __("Yard Zone"),
			"fieldtype": "Select",
			"options": "\nStorage_Yard_A\nStorage_Yard_B\nCleaning_Bay_C\nWorkshop_D\nSurvey_Lane_E\nGate_F\nPreClean_Buffer"
		}
	]
};
