// Copyright (c) 2026, Hidayatali and contributors

frappe.provide("kisan_customization.master_groups");

const RENTAL_ITEM_GROUP =
	kisan_customization.master_groups.RENTAL_ITEM_GROUP || "Rental Commodity";

frappe.ui.form.on("Bag Configuration", {
	refresh(frm) {
		frm.set_query("commodity", () => ({
			filters: {
				item_group: RENTAL_ITEM_GROUP,
				disabled: 0,
			},
		}));
	},
	rate_type(frm) {
		if (frm.doc.rate_type === "General") {
			frm.set_value("commodity", "");
		}
	},
});
