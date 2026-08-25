// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Aggregator Booking", {
	setup(frm) {
		frm.set_query("aggregator", () => ({
			filters: {
				disabled: 0,
				supplier_group: "Aggregator",
			},
		}));
	},

	refresh(frm) {
		frm.set_query("aggregator", () => ({
			filters: {
				disabled: 0,
				supplier_group: "Aggregator",
			},
		}));

		toggle_commission_fields(frm);
		apply_booking_dates(frm);
		calculate_broker_commission(frm);

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
		calculate_broker_commission(frm);
	},

	total_qty(frm) {
		calculate_broker_commission(frm);
	},
});

frappe.ui.form.on("Aggregator Booking Item", {
	item_code(frm, cdt, cdn) {
		set_item_uom(frm, cdt, cdn);
		calculate_row_amount(frm, cdt, cdn);
	},

	qty(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},

	rate(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},

	items_remove(frm) {
		recalculate_totals(frm);
	},
});

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

function set_item_uom(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.item_code) return;

	frappe.db.get_value("Item", row.item_code, "stock_uom", (r) => {
		if (r?.stock_uom) {
			frappe.model.set_value(cdt, cdn, "uom", r.stock_uom);
		}
	});
}

function calculate_row_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const amount = flt(row.qty) * flt(row.rate);
	frappe.model.set_value(cdt, cdn, "amount", amount).then(() => {
		recalculate_totals(frm);
	});
}

function recalculate_totals(frm) {
	let total_qty = 0;
	let total_amount = 0;
	const suppliers = new Set();

	(frm.doc.items || []).forEach((row) => {
		total_qty += flt(row.qty);
		total_amount += flt(row.amount);
		if (row.supplier) suppliers.add(row.supplier);
	});

	frm.set_value("total_qty", total_qty);
	frm.set_value("total_amount", total_amount);
	frm.set_value("no_of_suppliers", suppliers.size);
	calculate_broker_commission(frm);
	apply_booking_dates(frm);
}
