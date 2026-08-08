// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Kisan Master Settings", {
	refresh(frm) {
		frm.set_query("broker_commission_expense_account", () => ({
			filters: {
				company: frm.doc.default_company || frappe.defaults.get_global_default("company"),
				is_group: 0,
				disabled: 0,
			},
		}));
	},
});
