// Copyright (c) 2026, Oak Depot Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Container', {
	refresh(frm) {
		if (!frm.is_new()) {
			// Add custom buttons for common actions
			frm.add_custom_button(__('Gate-In'), () => {
				frappe.call({
					method: 'container_depot.container_depot.doctype.container.container.create_gate_entry',
					args: {
						container_no: frm.doc.container_no
					},
					callback: (r) => {
						if (!r.exc) {
							frappe.msgprint('Gate Entry created');
						}
					}
				});
			});

			frm.add_custom_button(__('Inspection'), () => {
				frappe.new_doc('Inspection', {
					container: frm.doc.name
				});
			});
		}
	}
});
