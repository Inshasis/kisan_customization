// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Aggregator Booking", {
	setup(frm) {
		frm.set_query("aggregator", () => ({
			filters: {
				disabled: 0,
			},
		}));
	},

	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !frm.doc.purchase_orders?.length) return;

		frm.add_custom_button(__("View Purchase Orders"), () => {
			const names = frm.doc.purchase_orders.map((row) => row.purchase_order).filter(Boolean);
			if (!names.length) return;

			frappe.set_route("List", "Purchase Order", {
				name: ["in", names],
			});
		});
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
	let grand_total = 0;
	const suppliers = new Set();

	(frm.doc.items || []).forEach((row) => {
		total_qty += flt(row.qty);
		grand_total += flt(row.amount);
		if (row.supplier) suppliers.add(row.supplier);
	});

	frm.set_value("total_qty", total_qty);
	frm.set_value("grand_total", grand_total);
	frm.set_value("no_of_suppliers", suppliers.size);
}
