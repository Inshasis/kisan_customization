// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Deduction Type", {
	refresh(frm) {
		toggle_calculation_fields(frm);
	},

	qty_deducation(frm) {
		if (frm.doc.qty_deducation && frm.doc.calculation) {
			frm.set_value("calculation", "");
		}
		toggle_calculation_fields(frm);
	},
});

function toggle_calculation_fields(frm) {
	const is_qty = frm.doc.qty_deducation;

	frm.toggle_display("calculation", !is_qty);
	frm.toggle_display("required_value", is_qty);
	frm.toggle_display("tiered_calculation", is_qty);
	frm.toggle_display("deduction_category", is_qty);
}
