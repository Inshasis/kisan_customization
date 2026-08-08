// Copyright (c) 2026, Hidayatali and contributors

frappe.ui.form.on("Broker Commission", {
	refresh(frm) {
		frm.page.btn_secondary.hide();
		frm.disable_save();

		if (frm.doc.journal_entry) {
			frm.add_custom_button(__("Journal Entry"), () => {
				frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
			});
		}

		if (frm.doc.purchase_invoice) {
			frm.add_custom_button(__("Purchase Invoice"), () => {
				frappe.set_route("Form", "Purchase Invoice", frm.doc.purchase_invoice);
			});
		}
	},
});
