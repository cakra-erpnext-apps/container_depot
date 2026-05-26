// Copyright (c) 2026, Oak Depot Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Repair Order', {
	setup(frm) {
		// Set queries or pre-filters if needed
	},
	refresh(frm) {
		// Add indicators or status alerts based on status
		if (frm.doc.status === 'Draft') {
			frm.set_intro(__('Draft Repair Order. Please add estimation items and save.'), 'blue');
		} else if (frm.doc.status === 'Pending Approval') {
			frm.set_intro(__('Awaiting approval from the Principal.'), 'orange');
		} else if (frm.doc.status === 'Approved') {
			frm.set_intro(__('Approved. Ready to start repair work.'), 'green');
		} else if (frm.doc.status === 'In Progress') {
			frm.set_intro(__('Repair work is currently in progress in the workshop.'), 'yellow');
		} else if (frm.doc.status === 'Completed') {
			frm.set_intro(__('Repair completed. Container is ready for service.'), 'green');
		} else if (frm.doc.status === 'Cancelled') {
			frm.set_intro(__('This Repair Order has been cancelled.'), 'red');
		}
	},
	container(frm) {
		if (frm.doc.container) {
			// Fetch principal (owner) from Container record
			frappe.db.get_value('Container', frm.doc.container, 'principal', (r) => {
				if (r && r.principal) {
					frm.set_value('principal', r.principal);
				}
			});
		} else {
			frm.set_value('principal', '');
		}
	}
});

// Grid calculations for Repair Estimate Item child table
frappe.ui.form.on('Repair Estimate Item', {
	quantity(frm, cdt, cdn) {
		calculate_row_totals(frm, cdt, cdn);
	},
	unit_price(frm, cdt, cdn) {
		calculate_row_totals(frm, cdt, cdn);
	},
	labor_hours(frm, cdt, cdn) {
		calculate_row_totals(frm, cdt, cdn);
	},
	labor_rate(frm, cdt, cdn) {
		calculate_row_totals(frm, cdt, cdn);
	},
	estimation_items_remove(frm, cdt, cdn) {
		calculate_total_cost(frm);
	}
});

function calculate_row_totals(frm, cdt, cdn) {
	let row = frappe.get_doc(cdt, cdn);
	
	// Part cost calculation
	let quantity = flt(row.quantity || 0);
	let unit_price = flt(row.unit_price || 0);
	let total_price = quantity * unit_price;
	frappe.model.set_value(cdt, cdn, 'total_price', total_price);

	// Labor cost calculation
	let labor_hours = flt(row.labor_hours || 0);
	let labor_rate = flt(row.labor_rate || 0);
	let labor_total = labor_hours * labor_rate;
	frappe.model.set_value(cdt, cdn, 'labor_total', labor_total);

	// Recalculate parent overall total
	calculate_total_cost(frm);
}

function calculate_total_cost(frm) {
	let total_cost = 0;
	if (frm.doc.estimation_items) {
		frm.doc.estimation_items.forEach(row => {
			total_cost += flt(row.total_price || 0) + flt(row.labor_total || 0);
		});
	}
	frm.set_value('total_cost', total_cost);
}
