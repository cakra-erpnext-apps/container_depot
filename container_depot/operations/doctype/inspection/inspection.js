// Copyright (c) 2026, Oak Depot Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inspection', {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.inspection_type === "EIR-In") {
			// Add button to check photo completion
			frm.add_custom_button(__('Check Photo Completion'), () => {
				let views = frm.doc.exterior_photos.map(p => p.photo_view);
				let required = ["Front", "Back", "Left", "Right"];
				let missing = required.filter(v => !views.includes(v));

				if (missing.length > 0) {
					frappe.msgprint(`Missing exterior photos: ${missing.join(", ")}`);
				} else {
					frappe.msgprint("All 4 exterior photos uploaded!");
				}
			});
		}

		if (!frm.is_new() && frm.doc.has_damage) {
			// Show warning if damage exists but no damage log
			if (frm.doc.damage_log.length === 0) {
				frappe.warn(
					'No Damage Log',
					'Has Damage is checked but no damage entries recorded.',
					__('Continue')
				);
			}
		}
	},

	has_damage(frm) {
		if (frm.doc.has_damage) {
			frappe.prompt([
				{
					fieldname: 'damage_type',
					fieldtype: 'Select',
					label: __('Damage Type'),
					options: 'Gasket\nValve\nFrame\nDoor\nFloor\nInterior_Lining\nOther',
					reqd: 1
				},
				{
					fieldname: 'description',
					fieldtype: 'Small Text',
					label: __('Description'),
					reqd: 1
				}
			], (data) => {
				frm.add_child('damage_log', {
					damage_type: data.damage_type,
					damage_description: data.description,
					repair_status: 'Pending'
				});
				frm.refresh_field('damage_log');
			}, __('Add Damage Entry'));
		}
	},

	on_submit(frm) {
		frappe.msgprint('Inspection submitted successfully!');
	}
});
