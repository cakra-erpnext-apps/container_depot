// Copyright (c) 2026, Oak Depot Team and contributors
// For license information, please see license.txt

// Inspection (EIR) — Desk client script.
// House style mirrors container_booking.js (custom buttons, narrative comments).
// The damage-entry dialogs build Damage Entry rows whose mapping (component / area /
// default severity & description) matches the server builder in
// container_depot/operations/eir.py:create_eir — keep the two in sync.

frappe.ui.form.on('Inspection', {
	onload(frm) {
		frm.trigger('_set_queries');
	},

	refresh(frm) {
		frm.trigger('_set_queries');
		if (!frm.is_new() && frm.doc.inspection_type === 'EIR-In') {
			frm.add_custom_button(__('Check Photo Completion'), () => check_photo_completion(frm));
		}
		// Surface an inconsistency without blocking: damage flagged but no rows.
		if (!frm.is_new() && frm.doc.has_damage && (frm.doc.damage_log || []).length === 0) {
			frappe.warn(
				__('No Damage Log'),
				__('Has Damage is checked but no damage entries recorded.'),
				() => {},
				__('Continue'),
			);
		}
	},

	// Ticking "Has Damage" opens a single-row entry dialog with VALID Link fields.
	// Legacy bug (fixed here): this used a Select of component names (Gasket/Valve/…)
	// written straight into `damage_type`, which is now a Link -> EIR Damage Code — so
	// every value it produced was an invalid link. The dialog below uses the real
	// taxonomy and defaults the reqd Damage Entry fields the same way the server does.
	has_damage(frm) {
		if (frm.doc.has_damage) add_damage_entry(frm);
	},

	_set_queries(frm) {
		// Booking codes that are still live — issued (Active) or consumed at the
		// gate (Used) — never expired/cancelled/reissued.
		frm.set_query('booking_code', () => ({ filters: { state: ['in', ['Active', 'Used']] } }));
	},

	// Picking a Booking Code prefills the EIR header from the SAME whitelisted
	// function the PWA uses (see prefill_from_booking) — one prefill implementation.
	booking_code(frm) {
		if (frm.doc.booking_code) prefill_from_booking(frm);
	},
});

// --- B-D2: Damage Entry grid fetch triggers (manual in-grid editing) ---
// Mirror create_eir's mapping so a row built by hand matches one built by the
// checklist dialog / PWA: checklist item -> component + area, repair code ->
// estimated hours, damage code -> description + default severity.
frappe.ui.form.on('Damage Entry', {
	checklist_item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.checklist_item) return;
		frappe.db
			.get_value('EIR Checklist Item', row.checklist_item, ['printed_no', 'item_name', 'area'])
			.then((r) => {
				const ci = r.message || {};
				frappe.model.set_value(cdt, cdn, 'component', `${ci.printed_no}. ${ci.item_name}`);
				frappe.model.set_value(cdt, cdn, 'area', ci.area);
			});
	},

	repair_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.repair_code || row.estimated_repair_hours) return;
		frappe.db.get_value('EIR Repair Code', row.repair_code, 'standard_hours').then((r) => {
			const hours = (r.message || {}).standard_hours;
			if (hours) frappe.model.set_value(cdt, cdn, 'estimated_repair_hours', hours);
		});
	},

	damage_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.damage_type) return;
		if (!row.severity) frappe.model.set_value(cdt, cdn, 'severity', 'Minor');
		if (!row.damage_description) {
			frappe.db.get_value('EIR Damage Code', row.damage_type, 'description').then((r) => {
				const desc = (r.message || {}).description;
				const fresh = locals[cdt][cdn];
				if (desc && fresh && !fresh.damage_description) {
					frappe.model.set_value(cdt, cdn, 'damage_description', desc);
				}
			});
		}
	},
});

function check_photo_completion(frm) {
	const views = (frm.doc.exterior_photos || []).map((p) => p.photo_view);
	const missing = ['Front', 'Back', 'Left', 'Right'].filter((v) => !views.includes(v));
	if (missing.length) {
		frappe.msgprint(__('Missing exterior photos: {0}', [missing.join(', ')]));
	} else {
		frappe.msgprint(__('All 4 exterior photos uploaded!'));
	}
}

function add_damage_entry(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Add Damage Entry'),
		fields: [
			{ fieldname: 'checklist_item', fieldtype: 'Link', label: __('Checklist Item'), options: 'EIR Checklist Item' },
			{ fieldname: 'damage_type', fieldtype: 'Link', label: __('Damage Code'), options: 'EIR Damage Code' },
			{ fieldname: 'repair_code', fieldtype: 'Link', label: __('Repair Code'), options: 'EIR Repair Code' },
			{ fieldname: 'severity', fieldtype: 'Select', label: __('Severity'), options: 'Minor\nModerate\nMajor\nCritical', default: 'Minor' },
			{ fieldname: 'damage_description', fieldtype: 'Small Text', label: __('Description'), description: __('Optional — defaults to the damage code description or the item name.') },
		],
		primary_action_label: __('Add'),
		primary_action(values) {
			append_damage_row(frm, values).then(() => d.hide());
		},
	});
	d.show();
}

// Resolve a checklist item's printed_no / item_name / area (used to fill component+area).
function resolve_checklist(item_code) {
	if (!item_code) return Promise.resolve(null);
	return frappe.db
		.get_value('EIR Checklist Item', item_code, ['printed_no', 'item_name', 'area'])
		.then((r) => r.message || null);
}

// Append one Damage Entry, mirroring create_eir's mapping: component =
// "{printed_no}. {item_name}", area from the checklist item, severity defaults Minor,
// and a non-empty description (input -> damage code desc -> item name) so the reqd
// fields never trip validation.
function append_damage_row(frm, values) {
	return resolve_checklist(values.checklist_item).then((ci) => {
		const finish = (desc) => {
			frm.add_child('damage_log', {
				checklist_item: values.checklist_item || undefined,
				area: ci ? ci.area : undefined,
				component: ci ? `${ci.printed_no}. ${ci.item_name}` : undefined,
				damage_type: values.damage_type || undefined,
				repair_code: values.repair_code || undefined,
				damage_description: desc || (ci ? ci.item_name : __('Damage')),
				severity: values.severity || 'Minor',
				repair_status: 'Pending',
			});
			frm.refresh_field('damage_log');
		};
		const typed = (values.damage_description || '').trim();
		if (typed) return finish(typed);
		if (values.damage_type) {
			return frappe.db
				.get_value('EIR Damage Code', values.damage_type, 'description')
				.then((r) => finish((r.message || {}).description));
		}
		return finish('');
	});
}

// --- B-D4: prefill the EIR header from a Booking Code ---
// Calls the SAME whitelisted function the PWA uses
// (container_depot.ess.inspections.eir_prefill -> operations.eir.prefill). There is
// exactly one prefill implementation; Desk is just another caller of it. Only blank
// fields are filled, so manual input is never clobbered, and the derived ISO 6346
// prefix/number/cd are shown as a dashboard comment (display-only, never stored).
function prefill_from_booking(frm) {
	frappe.call({
		method: 'container_depot.ess.inspections.eir_prefill',
		args: { booking_code: frm.doc.booking_code },
		callback(r) {
			const d = r.message;
			if (!d) return;
			const fills = {
				container: d.container,
				vessel: d.ex_vessel,
				serial_no: d.serial_no,
				manufacture_date: d.manufacture_date,
				capacity: d.capacity,
				tare_weight: d.tare_weight,
				max_gross_weight: d.max_gross_weight,
				last_test_date: d.last_test_date,
				last_cargo: d.last_cargo,
				depot: d.depot,
				tank_owner: d.principal,
			};
			Object.keys(fills).forEach((f) => {
				if (fills[f] != null && fills[f] !== '' && !frm.doc[f]) frm.set_value(f, fills[f]);
			});
			if (d.prefix || d.number || d.cd) {
				frm.dashboard.clear_comment();
				frm.dashboard.add_comment(
					__('ISO 6346 — Prefix: {0} · Number: {1} · Cd: {2}', [
						d.prefix || '—',
						d.number || '—',
						d.cd || '—',
					]),
					'blue',
					true,
				);
			}
		},
	});
}
