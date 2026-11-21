// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Deduction Type", {
	setup(frm) {
		frm.set_query("related_account", () => ({
			filters: {
				company: frm.doc.company || "",
				is_group: 0,
			},
		}));
	},

	refresh(frm) {
		toggle_calculation_fields(frm);
	},

	company(frm) {
		if (frm.doc.related_account) {
			frm.set_value("related_account", "");
		}
	},

	qty_deducation(frm) {
		toggle_calculation_fields(frm);
	},
});

function toggle_calculation_fields(frm) {
	const is_qty = frm.doc.qty_deducation;

	frm.toggle_display("required_value", is_qty);
	frm.toggle_display("tiered_calculation", is_qty);
	frm.toggle_display("deduction_category", is_qty);

	if (is_qty) {
		frm.set_df_property(
			"calculation",
			"description",
			__(
				"Qty types: Actual − Required gives difference. Tiered Calculation ON uses tier ranges from Kisan Master Settings. Tiered OFF multiplies difference by tier multiplier for Actual value. Then this formula runs. Damage example: difference * charges_per_unit * total_gross_weight / 100. S/S example: difference * total_amount / 100."
			)
		);
	} else {
		frm.set_df_property(
			"calculation",
			"description",
			__(
				"Auto formula when Qty Deducation is off. Example: total_bags * charges_per_unit. Leave empty to use Charges per Unit directly."
			)
		);
	}
}
