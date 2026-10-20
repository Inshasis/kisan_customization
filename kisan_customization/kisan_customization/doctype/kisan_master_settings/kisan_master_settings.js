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

	after_save() {
		frappe.show_alert({
			message: __("Sidebar rules saved. Reloading desk…"),
			indicator: "green",
		});
		setTimeout(() => window.location.reload(), 600);
	},
});
