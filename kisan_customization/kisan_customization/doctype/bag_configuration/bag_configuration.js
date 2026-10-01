// Copyright (c) 2026, Hidayatali and contributors

const COLD_STORAGE_ITEM_GROUP = "Cold Storage Item";

frappe.ui.form.on("Bag Configuration", {
	refresh(frm) {
		frm.set_query("commodity", () => ({
			filters: {
				item_group: COLD_STORAGE_ITEM_GROUP,
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
