frappe.provide("kisan_customization.broker_commission");

kisan_customization.broker_commission.calculate = function (frm) {
	if (!frm.fields_dict.custom_broker_commission_amount) return;

	const commission_type = frm.doc.custom_commission_type;
	let commission_amount = 0;

	if (commission_type === "Percentage") {
		const net_amount = flt(frm.doc.net_total) || 0;
		const percent = flt(frm.doc.custom_commission_percent) || 0;
		commission_amount = (net_amount * percent) / 100;
	} else if (commission_type === "Total Qty") {
		const total_qty = flt(frm.doc.total_qty) || 0;
		const rate = flt(frm.doc.custom_commission_amount) || 0;
		commission_amount = total_qty * rate;
	}

	frm.set_value("custom_broker_commission_amount", commission_amount);
};

kisan_customization.broker_commission.bind = function (doctype) {
	frappe.ui.form.on(doctype, {
		setup(frm) {
			frm.set_query("custom_broker", function () {
				return {
					filters: {
						supplier_group: "Broker",
					},
				};
			});
		},

		custom_commission_type(frm) {
			frm.set_value("custom_commission_percent", 0);
			frm.set_value("custom_commission_amount", 0);
			kisan_customization.broker_commission.calculate(frm);
		},

		custom_commission_percent(frm) {
			kisan_customization.broker_commission.calculate(frm);
		},

		custom_commission_amount(frm) {
			kisan_customization.broker_commission.calculate(frm);
		},

		net_total(frm) {
			kisan_customization.broker_commission.calculate(frm);
		},

		total_qty(frm) {
			kisan_customization.broker_commission.calculate(frm);
		},

		refresh(frm) {
			kisan_customization.broker_commission.calculate(frm);
		},
	});
};
