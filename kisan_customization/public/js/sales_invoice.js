kisan_customization.broker_commission.bind("Sales Invoice");
kisan_customization.delivery_payment_days.bind("Sales Invoice");

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (!frm.is_new()) {
			add_broker_commission_button(frm);
		}
	},
});

function add_broker_commission_button(frm) {
	if (frm.doc.docstatus !== 1 || !frm.doc.custom_broker) return;

	frappe.db.get_value(
		"Broker Commission",
		{ sales_invoice: frm.doc.name, docstatus: 1 },
		"name",
		(r) => {
			if (!r?.name) return;
			frm.add_custom_button(__("Broker Commission"), () => {
				frappe.set_route("Form", "Broker Commission", r.name);
			});
		}
	);
}
