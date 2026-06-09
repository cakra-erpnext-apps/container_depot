// Depot Contract — the Price List lines are negotiated from a Base Price List.
//
// The Item picker on each line is filtered to Items priced in the contract's
// Base Price List. Picking an Item seeds the line from that Item Price: UoM
// (read-only), Rate and Manhour (editable defaults) which are then negotiated.
// "Get Items from Base Price List" (re)populates the lines from the whole list.
// On Active the contract publishes these lines as a customer Price List named
// after the contract (handled server-side). Each line's currency follows the
// contract currency so Rate / Manhour format in the Base Price List currency.
//
// Status is driven by workflow buttons (set_status), not picked from a dropdown.

function container_depot_transition(frm, target) {
	const go = () =>
		frappe.call({
			method: "container_depot.operations.doctype.depot_contract.depot_contract.set_status",
			args: { contract: frm.doc.name, target },
			freeze: true,
			freeze_message: __("Updating status…"),
			callback: () => frm.reload_doc(),
		});
	frappe.confirm(__("Move this contract to {0}?", [__(target)]), () => {
		// Persist any in-progress edits (e.g. negotiated lines) before transitioning.
		if (frm.is_dirty()) frm.save().then(go);
		else go();
	});
}

frappe.ui.form.on("Depot Contract", {
	onload(frm) {
		frm.trigger("_set_tariff_item_query");
	},
	refresh(frm) {
		frm.trigger("_set_tariff_item_query");
		frm.trigger("_set_status_actions");
		frm.trigger("_apply_edit_lock");
	},
	_set_status_actions(frm) {
		if (frm.is_new()) return;
		// Status is set by these buttons (the field is read-only), following the flow
		// Draft -> Negotiation -> Active -> Expired, with Void to cancel.
		const ACTIONS = {
			Draft: [["Start Negotiation", "Negotiation", "primary"], ["Cancel", "Void"]],
			Negotiation: [["Activate", "Active", "primary"], ["Back to Draft", "Draft"], ["Cancel", "Void"]],
			Active: [["Expire", "Expired"], ["Void", "Void"]],
		};
		(ACTIONS[frm.doc.status] || []).forEach(([label, target, type]) => {
			const btn = frm.add_custom_button(__(label), () => container_depot_transition(frm, target));
			if (type === "primary") btn.removeClass("btn-default").addClass("btn-primary");
		});
	},
	_apply_edit_lock(frm) {
		// Editable only in Draft / Negotiation; Active and terminal states are locked.
		const locked = !frm.is_new() && !["Draft", "Negotiation"].includes(frm.doc.status);
		[
			"customer", "currency", "base_price_list", "payment_type", "payment_terms",
			"credit_limit", "valid_from", "valid_to", "tariff_lines", "generate_lines",
			"company_docs", "esign_status", "signed_pdf",
		].forEach((f) => frm.set_df_property(f, "read_only", locked ? 1 : 0));
		if (frm.fields_dict.tariff_lines) {
			frm.fields_dict.tariff_lines.grid.cannot_add_rows = locked;
			frm.fields_dict.tariff_lines.grid.cannot_delete_rows = locked;
		}
	},
	currency(frm) {
		frm.trigger("_sync_line_currency");
	},
	base_price_list(frm) {
		frm.trigger("_set_tariff_item_query");
		if (!frm.doc.base_price_list) return;
		// Bind currency to the base rate card (published Item Prices inherit the
		// Price List currency). Lines are generated only on the button.
		frappe.db.get_value("Price List", frm.doc.base_price_list, "currency").then((r) => {
			if (r.message && r.message.currency) frm.set_value("currency", r.message.currency);
		});
	},
	generate_lines(frm) {
		frm.trigger("_generate_lines_from_base");
	},
	_set_tariff_item_query(frm) {
		// Base Price List picker: only customer-less rate cards that have Item Prices.
		frm.set_query("base_price_list", () => ({
			query: "container_depot.operations.doctype.depot_contract.depot_contract.base_price_list_query",
		}));
		frm.set_query("item", "tariff_lines", () => ({
			query: "container_depot.operations.doctype.depot_contract.depot_contract.tariff_item_query",
			filters: { base_price_list: frm.doc.base_price_list },
		}));
	},
	_sync_line_currency(frm) {
		(frm.doc.tariff_lines || []).forEach((row) => {
			row.currency = frm.doc.currency;
		});
		frm.refresh_field("tariff_lines");
	},
	_generate_lines_from_base(frm) {
		if (!frm.doc.base_price_list) {
			frappe.msgprint(__("Select a Base Price List first."));
			return;
		}
		frappe.call({
			method: "container_depot.operations.doctype.depot_contract.depot_contract.base_price_list_lines",
			args: { base_price_list: frm.doc.base_price_list },
			callback(r) {
				const rows = r.message || [];
				// Reset first so repeated clicks always mirror the base list.
				frm.clear_table("tariff_lines");
				if (!rows.length) {
					frm.refresh_field("tariff_lines");
					frappe.msgprint(
						__("No selling Item Prices found in {0}. Lines cleared.", [frm.doc.base_price_list])
					);
					return;
				}
				rows.forEach((d) => {
					const row = frm.add_child("tariff_lines");
					row.item = d.item;
					row.uom = d.uom;
					row.rate = d.rate;
					row.manhour_rate = d.manhour_rate;
					row.currency = frm.doc.currency;
				});
				frm.refresh_field("tariff_lines");
				frappe.show_alert({
					message: __("Added {0} line(s) from {1}.", [rows.length, frm.doc.base_price_list]),
					indicator: "green",
				});
			},
		});
	},
});

frappe.ui.form.on("Tariff Rate", {
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item) return;
		if (!frm.doc.base_price_list) {
			frappe.model.set_value(cdt, cdn, "item", null);
			frappe.msgprint(__("Select a Base Price List before adding items."));
			return;
		}
		frappe.call({
			method: "container_depot.operations.doctype.depot_contract.depot_contract.item_price_defaults",
			args: { base_price_list: frm.doc.base_price_list, item: row.item },
			callback(r) {
				const d = r.message;
				if (!d) return;
				frappe.model.set_value(cdt, cdn, "uom", d.uom || null);
				frappe.model.set_value(cdt, cdn, "rate", d.rate || 0);
				frappe.model.set_value(cdt, cdn, "manhour_rate", d.manhour_rate || 0);
				frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency || null);
			},
		});
	},
});
