frappe.provide("kisan_customization.delivery_payment_days");

kisan_customization.delivery_payment_days.get_base_date = function (frm) {
	return frm.doc.transaction_date || frm.doc.posting_date || frappe.datetime.get_today();
};

kisan_customization.delivery_payment_days.add_days = function (frm, days) {
	days = cint(days);
	if (days <= 0) return null;
	return frappe.datetime.add_days(
		kisan_customization.delivery_payment_days.get_base_date(frm),
		days
	);
};

kisan_customization.delivery_payment_days.apply_delivery_days = function (frm) {
	const days = frm.doc.custom_delivery_days;
	if (!days) return;

	const date = kisan_customization.delivery_payment_days.add_days(frm, days);
	if (!date) return;

	if (frm.doc.doctype === "Purchase Order") {
		frm.set_value("schedule_date", date).then(() => {
			(frm.doc.items || []).forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "schedule_date", date);
			});
			frm.refresh_field("items");
		});
	} else if (frm.doc.doctype === "Purchase Invoice") {
		if (frm.fields_dict.custom_required_by) {
			frm.set_value("custom_required_by", date);
		}
	}
};

kisan_customization.delivery_payment_days.apply_payment_days = function (frm) {
	const days = frm.doc.custom_payment_days;
	if (!days) return;

	const date = kisan_customization.delivery_payment_days.add_days(frm, days);
	if (!date) return;

	const schedule = frm.doc.payment_schedule || [];

	if (!schedule.length) {
		const row = frm.add_child("payment_schedule");
		row.due_date = date;
		row.invoice_portion = 100;
		const amount = flt(frm.doc.rounded_total) || flt(frm.doc.grand_total);
		if (amount) {
			row.payment_amount = amount;
			row.outstanding = amount;
		}
		frm.refresh_field("payment_schedule");
		return;
	}

	schedule.forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "due_date", date);
	});
	frm.refresh_field("payment_schedule");
};

kisan_customization.delivery_payment_days.apply_all = function (frm) {
	if (frm.doc.custom_delivery_days) {
		kisan_customization.delivery_payment_days.apply_delivery_days(frm);
	}
	if (frm.doc.custom_payment_days) {
		kisan_customization.delivery_payment_days.apply_payment_days(frm);
	}
};

kisan_customization.delivery_payment_days.bind = function (doctype) {
	const handlers = {
		custom_delivery_days(frm) {
			kisan_customization.delivery_payment_days.apply_delivery_days(frm);
		},
		custom_payment_days(frm) {
			kisan_customization.delivery_payment_days.apply_payment_days(frm);
		},
	};

	if (doctype === "Purchase Order") {
		handlers.transaction_date = function (frm) {
			kisan_customization.delivery_payment_days.apply_all(frm);
		};
	} else if (doctype === "Purchase Invoice") {
		handlers.posting_date = function (frm) {
			kisan_customization.delivery_payment_days.apply_all(frm);
		};
	}

	frappe.ui.form.on(doctype, handlers);
};
