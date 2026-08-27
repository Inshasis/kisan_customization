// Copyright (c) 2026, Hidayatali and contributors

const BOOKING_SUPPLIER_GROUP = "Purchase";
const BOOKING_ITEM_GROUP = "Products";
const BOOKING_UOM = "Quintal";

frappe.ui.form.on("Aggregator Booking", {
	setup(frm) {
		apply_booking_filters(frm);
	},

	onload(frm) {
		apply_booking_filters(frm);
	},

	refresh(frm) {
		apply_booking_filters(frm);
		setup_commodity_buttons(frm);
		setup_commodities_grid_readonly(frm);
		patch_commodity_grid_edit(frm);
		toggle_commission_fields(frm);
		toggle_discount_fields(frm);
		apply_booking_dates(frm);
		recalculate_commodity_allocations(frm);
		recalculate_totals(frm);

		if (frm.doc.docstatus !== 1 || !frm.doc.purchase_orders?.length) return;

		frm.add_custom_button(__("View Purchase Orders"), () => {
			const names = frm.doc.purchase_orders.map((row) => row.purchase_order).filter(Boolean);
			if (!names.length) return;

			frappe.set_route("List", "Purchase Order", {
				name: ["in", names],
			});
		});
	},

	booking_date(frm) {
		apply_booking_dates(frm);
	},

	delivery_days(frm) {
		apply_booking_dates(frm);
	},

	payment_days(frm) {
		apply_booking_dates(frm);
	},

	additional_discount_percentage(frm) {
		calculate_booking_discount(frm);
		toggle_discount_fields(frm);
	},

	discount_amount(frm) {
		if (frm._updating_discount_from_percent) {
			return;
		}
		if (flt(frm.doc.discount_amount)) {
			frm.doc.additional_discount_percentage = 0;
			frm.refresh_field("additional_discount_percentage");
		}
		calculate_booking_discount(frm);
		toggle_discount_fields(frm);
	},

	commission_type(frm) {
		if (frm.doc.commission_type === "Percentage") {
			frm.set_value("commission_amount", 0);
		} else if (frm.doc.commission_type === "Total Qty") {
			frm.set_value("commission_percent", 0);
		} else {
			frm.set_value("commission_percent", 0);
			frm.set_value("commission_amount", 0);
		}
		toggle_commission_fields(frm);
		calculate_broker_commission(frm);
	},

	commission_percent(frm) {
		calculate_broker_commission(frm);
	},

	commission_amount(frm) {
		calculate_broker_commission(frm);
	},

	total_amount(frm) {
		calculate_booking_discount(frm);
		calculate_broker_commission(frm);
	},

	total_qty(frm) {
		calculate_broker_commission(frm);
	},

	commodities_remove(frm) {
		remove_supplier_rows_for_missing_commodities(frm);
		recalculate_commodity_allocations(frm);
		recalculate_totals(frm);
	},
});

frappe.ui.form.on("Aggregator Booking Item", {
	item_code(frm, cdt, cdn) {
		populate_item_row_from_commodity(frm, cdt, cdn);
	},

	supplier(frm, cdt, cdn) {
		populate_item_row_from_commodity(frm, cdt, cdn);
	},

	qty(frm, cdt, cdn) {
		if (!validate_child_qty_limit(frm, cdt, cdn)) {
			return;
		}
		calculate_row_amount(frm, cdt, cdn);
	},

	items_remove(frm) {
		recalculate_commodity_allocations(frm);
		recalculate_totals(frm);
	},
});

function apply_booking_filters(frm) {
	frm.set_query("aggregator", () => ({
		filters: {
			disabled: 0,
			supplier_group: "Aggregator",
		},
	}));

	frm.set_query("item_code", "items", () => ({
		filters: {
			name: ["in", get_booking_commodity_items(frm)],
		},
	}));

	frm.set_query("supplier", "items", () => ({
		filters: {
			disabled: 0,
			supplier_group: BOOKING_SUPPLIER_GROUP,
		},
	}));
}

function get_booking_commodity_items(frm) {
	const items = (frm.doc.commodities || []).map((row) => row.item_code).filter(Boolean);
	return items.length ? items : ["__none__"];
}

function setup_commodity_buttons(frm) {
	if (frm.doc.docstatus !== 0) {
		return;
	}

	frm.add_custom_button(__("Add Commodity"), () => open_commodity_dialog(frm));
}

function setup_commodities_grid_readonly(frm) {
	const grid = frm.fields_dict.commodities?.grid;
	if (!grid) {
		return;
	}

	grid.wrapper.find(".grid-add-row").hide();
	grid.wrapper.find(".grid-footer .btn").hide();
	grid.wrapper.find(".grid-remove-rows").hide();
	grid.wrapper.find(".grid-row-check").hide();
}

function patch_commodity_grid_edit(frm) {
	const grid = frm.fields_dict.commodities?.grid;
	if (!grid || grid.__booking_commodity_edit_patched) {
		return;
	}

	grid.wrapper.on("click", ".grid-row", function () {
		if (frm.doc.docstatus !== 0) {
			return;
		}

		const idx = cint($(this).attr("data-idx"));
		const row = frm.doc.commodities?.[idx - 1];
		if (row?.name) {
			open_commodity_dialog(frm, row.name);
		}
	});

	grid.__booking_commodity_edit_patched = true;
}

function open_commodity_dialog(frm, cdn = null) {
	if (frm.doc.docstatus !== 0) {
		return;
	}

	const is_edit = !!cdn;
	const existing_row = is_edit ? locals["Aggregator Booking Commodity"]?.[cdn] : null;

	const dialog = new frappe.ui.Dialog({
		title: is_edit ? __("Edit Commodity") : __("Add Commodity"),
		fields: [
			{
				fieldname: "item_code",
				label: __("Commodity"),
				fieldtype: "Link",
				options: "Item",
				reqd: 1,
				get_query() {
					const existing = (frm.doc.commodities || [])
						.map((row) => row.item_code)
						.filter((item) => item && item !== existing_row?.item_code);

					return {
						query: "erpnext.controllers.queries.item_query",
						filters: {
							item_group: BOOKING_ITEM_GROUP,
							is_purchase_item: 1,
							has_variants: 0,
							name: ["not in", existing.length ? existing : ["__none__"]],
						},
					};
				},
			},
			{
				fieldname: "rate",
				label: __("Rate"),
				fieldtype: "Currency",
				reqd: 1,
				non_negative: 1,
			},
			{
				fieldname: "aggregator_qty",
				label: __("Aggregator Qty"),
				fieldtype: "Float",
				reqd: 1,
				non_negative: 1,
			},
		],
		primary_action_label: is_edit ? __("Update") : __("Add"),
		primary_action(values) {
			save_commodity_from_dialog(frm, values, cdn);
			dialog.hide();
		},
	});

	if (existing_row) {
		dialog.set_values({
			item_code: existing_row.item_code,
			rate: existing_row.rate,
			aggregator_qty: existing_row.aggregator_qty,
		});
	}

	dialog.show();
}

function save_commodity_from_dialog(frm, values, cdn = null) {
	const item_code = values.item_code;
	const rate = flt(values.rate);
	const aggregator_qty = flt(values.aggregator_qty);

	if (!item_code || rate < 0 || aggregator_qty <= 0) {
		frappe.msgprint({
			title: __("Invalid Commodity"),
			message: __("Commodity, Rate, and Aggregator Qty are required."),
			indicator: "orange",
		});
		return;
	}

	const duplicate = (frm.doc.commodities || []).find(
		(row) => row.item_code === item_code && row.name !== cdn
	);
	if (duplicate) {
		frappe.msgprint({
			title: __("Duplicate Commodity"),
			message: __("Commodity {0} is already added.", [item_code]),
			indicator: "orange",
		});
		return;
	}

	frappe.db.get_value("Item", item_code, "item_name", (r) => {
		frm.set_df_property("commodities", "read_only", 0);

		if (cdn) {
			const row = locals["Aggregator Booking Commodity"][cdn];
			const old_item = row.item_code;

			row.item_code = item_code;
			row.item_name = r?.item_name || "";
			row.rate = rate;
			row.aggregator_qty = aggregator_qty;
			row.amount = aggregator_qty * rate;

			if (old_item !== item_code) {
				remove_supplier_rows_for_item(frm, old_item);
			}

			sync_supplier_rows_for_item(frm, item_code);
		} else {
			const child = frm.add_child("commodities");
			child.item_code = item_code;
			child.item_name = r?.item_name || "";
			child.rate = rate;
			child.aggregator_qty = aggregator_qty;
			child.allocated_qty = 0;
			child.amount = aggregator_qty * rate;
		}

		frm.refresh_field("commodities");
		frm.set_df_property("commodities", "read_only", 1);
		setup_commodities_grid_readonly(frm);
		recalculate_commodity_allocations(frm);
		sync_all_items_from_commodities(frm);
		recalculate_totals(frm);
	});
}

function populate_item_row_from_commodity(frm, cdt, cdn) {
	const row = locals[cdt]?.[cdn];
	if (!row) {
		return;
	}

	if (!frm.doc.commodities?.length) {
		frappe.msgprint({
			title: __("Commodity Required"),
			message: __("Please add Commodity Details before adding supplier rows."),
			indicator: "orange",
		});
		return;
	}

	if (!row.item_code) {
		return;
	}

	const commodity = (frm.doc.commodities || []).find((c) => c.item_code === row.item_code);
	if (!commodity) {
		frappe.msgprint({
			title: __("Invalid Item"),
			message: __("Item {0} is not in Commodity Details.", [row.item_code]),
			indicator: "orange",
		});
		row.item_code = "";
		frm.refresh_field("items");
		return;
	}

	row.item_name = commodity.item_name || row.item_name;
	row.rate = flt(commodity.rate);
	row.uom = BOOKING_UOM;
	row.amount = flt(row.qty) * flt(row.rate);
	frm.refresh_field("items");
}

function sync_all_items_from_commodities(frm) {
	(frm.doc.items || []).forEach((row) => {
		if (!row.name) {
			return;
		}
		populate_item_row_from_commodity(frm, row.doctype, row.name);
	});
	frm.refresh_field("items");
}

function sync_supplier_rows_for_item(frm, item_code) {
	(frm.doc.items || []).forEach((row) => {
		if (row.item_code === item_code && row.name) {
			populate_item_row_from_commodity(frm, row.doctype, row.name);
		}
	});
}

function remove_supplier_rows_for_item(frm, item_code) {
	const to_remove = (frm.doc.items || []).filter((row) => row.item_code === item_code);
	to_remove.forEach((row) => {
		frm.get_field("items").grid.grid_rows_by_docname[row.name]?.remove();
	});
}

function remove_supplier_rows_for_missing_commodities(frm) {
	const valid_items = new Set(get_booking_commodity_items(frm));
	(frm.doc.items || [])
		.filter((row) => row.item_code && !valid_items.has(row.item_code))
		.forEach((row) => {
			frm.get_field("items").grid.grid_rows_by_docname[row.name]?.remove();
		});
}

function get_allocated_qty_for_item(frm, item_code, exclude_cdn = null) {
	let total = 0;

	(frm.doc.items || []).forEach((row) => {
		if (exclude_cdn && row.name === exclude_cdn) {
			return;
		}
		if (row.item_code === item_code) {
			total += flt(row.qty);
		}
	});

	return total;
}

function validate_child_qty_limit(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.item_code) {
		return true;
	}

	const commodity = (frm.doc.commodities || []).find((c) => c.item_code === row.item_code);
	if (!commodity) {
		return true;
	}

	const limit = flt(commodity.aggregator_qty);
	const other_total = get_allocated_qty_for_item(frm, row.item_code, cdn);
	const new_total = other_total + flt(row.qty);

	if (new_total > limit) {
		frappe.msgprint({
			title: __("Qty Limit Exceeded"),
			message: __(
				"Allocated quantity for {0} ({1}) cannot exceed Aggregator Qty ({2}).",
				[row.item_code, new_total, limit]
			),
			indicator: "orange",
		});
		frappe.model.set_value(cdt, cdn, "qty", 0);
		return false;
	}

	return true;
}

function recalculate_commodity_allocations(frm) {
	(frm.doc.commodities || []).forEach((commodity) => {
		if (!commodity.item_code) {
			return;
		}
		commodity.allocated_qty = get_allocated_qty_for_item(frm, commodity.item_code);
		commodity.amount = flt(commodity.aggregator_qty) * flt(commodity.rate);
	});
	frm.refresh_field("commodities");
}

function get_booking_base_date(frm) {
	return frm.doc.booking_date || frappe.datetime.get_today();
}

function apply_booking_dates(frm) {
	const base_date = get_booking_base_date(frm);
	const delivery_days = cint(frm.doc.delivery_days);
	const payment_days = cint(frm.doc.payment_days);

	if (delivery_days > 0 && base_date) {
		frm.set_value("delivery_date", frappe.datetime.add_days(base_date, delivery_days));
	} else {
		frm.set_value("delivery_date", base_date || null);
	}

	if (payment_days > 0 && base_date) {
		frm.set_value("payment_date", frappe.datetime.add_days(base_date, payment_days));
	} else {
		frm.set_value("payment_date", null);
	}
}

function toggle_commission_fields(frm) {
	const commission_type = frm.doc.commission_type;
	frm.toggle_display("commission_percent", commission_type === "Percentage");
	frm.toggle_display("commission_amount", commission_type === "Total Qty");
}

function toggle_discount_fields(frm) {
	const use_percent = flt(frm.doc.additional_discount_percentage) > 0;
	const use_amount = !use_percent && flt(frm.doc.discount_amount) > 0;

	frm.toggle_enable("discount_amount", !use_percent);
	frm.toggle_enable("additional_discount_percentage", !use_amount);
}

function calculate_booking_discount(frm) {
	const total_amount = flt(frm.doc.total_amount) || 0;
	const percent = flt(frm.doc.additional_discount_percentage) || 0;
	let discount = 0;

	if (percent > 0) {
		discount = (total_amount * percent) / 100;
	} else {
		discount = flt(frm.doc.discount_amount) || 0;
	}

	const net_amount = Math.max(0, total_amount - discount);

	frm._updating_discount_from_percent = true;
	frm.doc.discount_amount = discount;
	frm.doc.net_amount = net_amount;
	frm.refresh_field("discount_amount");
	frm.refresh_field("net_amount");
	frm._updating_discount_from_percent = false;
}

function calculate_broker_commission(frm) {
	const commission_type = frm.doc.commission_type;
	let broker_commission_amount = 0;

	if (commission_type === "Percentage") {
		const total_amount = flt(frm.doc.total_amount) || 0;
		const percent = flt(frm.doc.commission_percent) || 0;
		broker_commission_amount = (total_amount * percent) / 100;
	} else if (commission_type === "Total Qty") {
		const total_qty = flt(frm.doc.total_qty) || 0;
		const rate = flt(frm.doc.commission_amount) || 0;
		broker_commission_amount = total_qty * rate;
	}

	frm.set_value("broker_commission_amount", broker_commission_amount);
}

function calculate_row_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const amount = flt(row.qty) * flt(row.rate);
	frappe.model.set_value(cdt, cdn, "amount", amount).then(() => {
		recalculate_commodity_allocations(frm);
		recalculate_totals(frm);
	});
}

function recalculate_totals(frm) {
	let total_qty = 0;
	let total_amount = 0;
	const suppliers = new Set();

	(frm.doc.items || []).forEach((row) => {
		if (!row.supplier && !row.item_code && !flt(row.qty) && !flt(row.rate)) {
			return;
		}

		total_qty += flt(row.qty);
		total_amount += flt(row.amount);
		if (row.supplier) suppliers.add(row.supplier);
	});

	frm.set_value("total_qty", total_qty);
	frm.set_value("total_amount", total_amount);
	frm.set_value("no_of_suppliers", suppliers.size);
	calculate_booking_discount(frm);
	calculate_broker_commission(frm);
	apply_booking_dates(frm);
}
