frappe.query_reports["Gasket Inventory Status"] = {
	"filters": [
		{
			"fieldname": "type",
			"label": __("Gasket Type"),
			"fieldtype": "Select",
			"options": "\nPTFE\nEPDM\nSilicone\nFKM (Viton)\nNeoprene\nOther"
		}
	]
};
