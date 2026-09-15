// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Bag Configuration", {
	rate_type(frm) {
		if (frm.doc.rate_type === "General") {
			frm.set_value("commodity", "");
		}
	},
});
