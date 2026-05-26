// Copyright (c) 2026, Oak Depot Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Voucher', {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.voucher_type === "Gate_In (Bon Bongkar)") {
			// Add button to validate QR code
			frm.add_custom_button(__('Validate QR'), () => {
				frappe.call({
					method: 'container_depot.container_depot.doctype.voucher.voucher.validate_qr',
					args: {
						voucher_id: frm.doc.voucher_id
					},
					callback: (r) => {
						if (r.message) {
							frappe.msgprint(`QR Valid: ${r.message}`);
						}
					}
				});
			});
		}

		if (!frm.is_new() && frm.doc.voucher_type === "Gate_Out (Release)") {
			// Add button to generate release DO
			frm.add_custom_button(__('Generate Release DO'), () => {
				frappe.call({
					method: 'container_depot.container_depot.doctype.voucher.voucher.generate_release_do',
					args: {
						voucher_id: frm.doc.name
					},
					callback: (r) => {
						if (!r.exc) {
							frappe.msgprint('Release DO generated');
						}
					}
				});
			});
		}
	}
});
