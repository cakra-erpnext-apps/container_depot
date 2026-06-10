// Copyright (c) 2026, Oak Depot Team and contributors
// For license information, please see license.txt

// A single bon/voucher carries at most this many containers.
const MAX_CONTAINERS_PER_ORDER = 2;

frappe.ui.form.on('Order Bongkar', {
	refresh(frm) {
		// Add/revise: only this booking's still-pending (Active) Booking Codes.
		// Codes already placed on another, unfinished voucher are Used, so they
		// won't appear here.
		frm.set_query('booking_code', 'containers', () => ({
			filters: { booking: frm.doc.booking, state: 'Active' }
		}));
		// Manual add picks a Container — restrict it to containers with an Active
		// Booking Code on THIS voucher's booking, so a single bon can never mix
		// containers from different bookings (one booking → many vouchers, but a
		// voucher → one booking).
		frm.set_query('container', 'containers', () => ({
			query: 'container_depot.operations.doctype.order_bongkar.order_bongkar.pending_container_query',
			filters: { booking: frm.doc.booking },
		}));
		const grid = frm.fields_dict.containers.grid;
		// A Bon Bongkar has no cleaning certificate.
		grid.update_docfield_property('cleaning_certificate', 'hidden', 1);
		_strip_row_buttons(frm);
		_enforce_max_rows(frm);
		grid.refresh();
	},
	booking(frm) {
		_default_shipper(frm);
		_default_principal(frm);
	}
});

function _default_shipper(frm) {
	if (frm.doc.booking && !frm.doc.shipper) {
		frappe.db.get_value('Container Booking', frm.doc.booking, 'customer', (r) => {
			if (r && r.customer) frm.set_value('shipper', r.customer);
		});
	}
}

function _default_principal(frm) {
	if (frm.doc.booking && !frm.doc.principal) {
		frappe.db.get_value('Container Booking', frm.doc.booking, 'principal', (r) => {
			if (r && r.principal) frm.set_value('principal', r.principal);
		});
	}
}

// Editing a container row should only let the operator tweak that row's values —
// not spawn extra rows. Hide Insert Above / Insert Below / Duplicate (which is how a
// duplicate Booking Code row appeared); the collapse (save) + Delete stay.
function _strip_row_buttons(frm) {
	frm.fields_dict.containers.grid.wrapper.addClass('ob-no-row-insert');
	if (!document.getElementById('ob-grid-row-style')) {
		const style = document.createElement('style');
		style.id = 'ob-grid-row-style';
		style.textContent =
			'.ob-no-row-insert .grid-insert-row,' +
			'.ob-no-row-insert .grid-insert-row-below,' +
			'.ob-no-row-insert .grid-duplicate-row,' +
			'.ob-no-row-insert .grid-append-row { display: none !important; }';
		document.head.appendChild(style);
	}
}

// Cap the grid at MAX_CONTAINERS_PER_ORDER: block the Add Row button past the cap
// (the server validate enforces the same 1..MAX as the hard guarantee).
function _enforce_max_rows(frm) {
	const grid = frm.fields_dict.containers.grid;
	grid.cannot_add_rows = (frm.doc.containers || []).length >= MAX_CONTAINERS_PER_ORDER;
	if (!grid._max_patched) {
		const orig = grid.add_new_row.bind(grid);
		grid.add_new_row = function (...args) {
			if ((frm.doc.containers || []).length >= MAX_CONTAINERS_PER_ORDER) {
				frappe.show_alert({
					message: __('Max {0} containers per voucher.', [MAX_CONTAINERS_PER_ORDER]),
					indicator: 'orange',
				});
				return;
			}
			return orig(...args);
		};
		grid._max_patched = true;
	}
}
