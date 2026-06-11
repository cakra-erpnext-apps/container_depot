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
		// Full-grid checklist entry (parity with the PWA) — drafts only.
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Isi Checklist EIR'), () => open_checklist_dialog(frm));
		}
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

	// The EIR inspects a physical container, so picking the Container prefills the
	// header from the SAME whitelisted function the PWA uses (see
	// prefill_from_container) — one prefill implementation, keyed on the container.
	container(frm) {
		if (frm.doc.container) prefill_from_container(frm);
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

// --- B-D4: prefill the EIR header from the Container ---
// Calls the SAME whitelisted function the PWA uses
// (container_depot.ess.inspections.eir_prefill -> operations.eir.prefill). There is
// exactly one prefill implementation; Desk is just another caller of it, keyed on the
// container number. Native fetch_from already fills serial/capacity/etc. from the
// container; this adds depot, tank owner and the display-only ISO 6346 derive. Only
// blank fields are filled, so manual input is never clobbered.
function prefill_from_container(frm) {
	frappe.call({
		method: 'container_depot.ess.inspections.eir_prefill',
		args: { container: frm.doc.container },
		callback(r) {
			const d = r.message;
			if (!d) return;
			const fills = {
				depot: d.depot,
				tank_owner: d.principal,
				vessel: d.ex_vessel,
				serial_no: d.serial_no,
				manufacture_date: d.manufacture_date,
				capacity: d.capacity,
				tare_weight: d.tare_weight,
				max_gross_weight: d.max_gross_weight,
				last_test_date: d.last_test_date,
				last_cargo: d.last_cargo,
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

// --- B-D3: "Isi Checklist EIR" — full 50-row grid dialog (parity with the PWA) ---
// Loads the checklist + code lists once (same masters as the PWA), pre-populates from
// existing checklist-linked Damage Entry rows so the button REVISES (matched by
// checklist_item) instead of duplicating, and on Terapkan upserts only the filled
// rows — applying the same mapping as operations/eir.py:create_eir.
function open_checklist_dialog(frm) {
	frappe.call({
		method: 'container_depot.ess.inspections.eir_masters',
		callback(r) {
			const m = r.message || {};
			const checklist = m.checklist || [];
			const damageCodes = m.damage_codes || [];
			const repairCodes = m.repair_codes || [];
			const descByCode = {};
			damageCodes.forEach((c) => {
				descByCode[c.code] = c.description;
			});

			// Existing checklist-linked rows -> pre-populate (idempotent revise).
			const existing = {};
			(frm.doc.damage_log || []).forEach((row) => {
				if (row.checklist_item) existing[row.checklist_item] = row;
			});

			const d = new frappe.ui.Dialog({
				title: __('Isi Checklist EIR'),
				size: 'extra-large',
				fields: [{ fieldname: 'grid_html', fieldtype: 'HTML' }],
				primary_action_label: __('Terapkan'),
				primary_action() {
					apply_checklist(frm, d, checklist, descByCode);
					d.hide();
				},
			});

			const $w = d.fields_dict.grid_html.$wrapper;
			$w.html(render_checklist_html(checklist, damageCodes, repairCodes, existing));
			// Pre-select the existing code values (selects can't be set via markup here).
			Object.keys(existing).forEach((code) => {
				const row = existing[code];
				if (row.damage_type) $w.find(`.eir-dmg[data-item="${code}"]`).val(row.damage_type);
				if (row.repair_code) $w.find(`.eir-rep[data-item="${code}"]`).val(row.repair_code);
			});
			d.show();
		},
	});
}

function render_checklist_html(checklist, damageCodes, repairCodes, existing) {
	const esc = frappe.utils.escape_html;
	const opts = (list) =>
		['<option value=""></option>']
			.concat(list.map((c) => `<option value="${esc(c.code)}">${esc(c.code)} — ${esc(c.description || '')}</option>`))
			.join('');
	const dmgOpts = opts(damageCodes);
	const repOpts = opts(repairCodes);

	let html = `<div style="max-height:60vh;overflow:auto">
		<table class="table table-bordered" style="font-size:12px;margin-bottom:0">
			<thead><tr>
				<th style="width:34%">${__('Item')}</th>
				<th style="width:22%">${__('Kode Kerusakan')}</th>
				<th style="width:22%">${__('Kode Perbaikan')}</th>
				<th style="width:22%">${__('Keterangan')}</th>
			</tr></thead><tbody>`;

	let lastArea = null;
	checklist.forEach((item) => {
		if (item.area !== lastArea) {
			lastArea = item.area;
			html += `<tr style="background:#f5f5f5"><td colspan="4"><b>${esc(item.area)}</b></td></tr>`;
		}
		const ex = existing[item.item_code] || {};
		const rmk = ex.damage_description ? esc(ex.damage_description) : '';
		html += `<tr>
			<td>${esc(item.printed_no)}. ${esc(item.item_name)}</td>
			<td><select class="form-control eir-dmg" data-item="${esc(item.item_code)}">${dmgOpts}</select></td>
			<td><select class="form-control eir-rep" data-item="${esc(item.item_code)}">${repOpts}</select></td>
			<td><input class="form-control eir-rmk" data-item="${esc(item.item_code)}" type="text" value="${rmk}"></td>
		</tr>`;
	});
	html += '</tbody></table></div>';
	return html;
}

function apply_checklist(frm, d, checklist, descByCode) {
	const $w = d.fields_dict.grid_html.$wrapper;
	const existingByItem = {};
	(frm.doc.damage_log || []).forEach((row) => {
		if (row.checklist_item) existingByItem[row.checklist_item] = row;
	});

	const keep = new Set();
	checklist.forEach((item) => {
		const code = item.item_code;
		const dmg = ($w.find(`.eir-dmg[data-item="${code}"]`).val() || '').trim();
		const rep = ($w.find(`.eir-rep[data-item="${code}"]`).val() || '').trim();
		const rmk = ($w.find(`.eir-rmk[data-item="${code}"]`).val() || '').trim();
		if (!dmg && !rep && !rmk) return; // Acceptable / cleared — not stored.

		const desc = rmk || (dmg ? descByCode[dmg] : '') || item.item_name;
		let row = existingByItem[code];
		if (!row) row = frm.add_child('damage_log', { checklist_item: code });
		row.component = `${item.printed_no}. ${item.item_name}`;
		row.area = item.area;
		row.damage_type = dmg || null;
		row.repair_code = rep || null;
		row.damage_description = desc;
		if (!row.severity) row.severity = 'Minor';
		keep.add(code);
	});

	// Drop checklist-linked rows the user cleared; leave manual (non-checklist) rows.
	frm.doc.damage_log = (frm.doc.damage_log || []).filter(
		(row) => !row.checklist_item || keep.has(row.checklist_item),
	);
	// has_damage reflects any real damage code (not "v") across the whole log.
	const hasDamage = (frm.doc.damage_log || []).some((row) => row.damage_type && row.damage_type !== 'v');
	frm.set_value('has_damage', hasDamage ? 1 : 0);
	frm.refresh_field('damage_log');
}
