frappe.provide("kisan_customization.delivery_payment_days");

kisan_customization.delivery_payment_days.get_base_date = function (frm) {
	if (frm.doc.doctype === "Purchase Invoice") {
		return frm.doc.posting_date || frm.doc.bill_date || frappe.datetime.get_today();
	}
	return frm.doc.transaction_date || frm.doc.posting_date || frappe.datetime.get_today();
};

kisan_customization.delivery_payment_days.get_totals = function (frm) {
	return {
		grand_total: flt(frm.doc.rounded_total) || flt(frm.doc.grand_total) || 0,
		base_grand_total: flt(frm.doc.base_rounded_total) || flt(frm.doc.base_grand_total) || 0,
	};
};

kisan_customization.delivery_payment_days.set_row_amounts = function (row, totals) {
	const portion = flt(row.invoice_portion) || 100;
	const payment_amount = (totals.grand_total * portion) / 100;
	const base_payment_amount = (totals.base_grand_total * portion) / 100;

	row.payment_amount = payment_amount;
	row.base_payment_amount = base_payment_amount;
	row.outstanding = payment_amount;
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

	if (frm.doc.doctype !== "Purchase Order") {
		return;
	}

	frm.set_value("schedule_date", date).then(() => {
		(frm.doc.items || []).forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, "schedule_date", date);
		});
		frm.refresh_field("items");
	});
};

kisan_customization.delivery_payment_days.sync_payment_amounts = function (frm) {
	const schedule = frm.doc.payment_schedule || [];
	if (!schedule.length) return;

	const totals = kisan_customization.delivery_payment_days.get_totals(frm);
	schedule.forEach((row) => {
		kisan_customization.delivery_payment_days.set_row_amounts(row, totals);
	});
};

kisan_customization.delivery_payment_days.apply_payment_days = function (frm) {
	const days = frm.doc.custom_payment_days;
	if (!days) return;

	const date = kisan_customization.delivery_payment_days.add_days(frm, days);
	if (!date) return;

	const totals = kisan_customization.delivery_payment_days.get_totals(frm);
	const schedule = frm.doc.payment_schedule || [];

	if (!schedule.length) {
		const row = frm.add_child("payment_schedule");
		row.due_date = date;
		row.invoice_portion = 100;
		kisan_customization.delivery_payment_days.set_row_amounts(row, totals);
		frm.refresh_field("payment_schedule");
		if (frm.fields_dict.due_date) {
			frm.set_value("due_date", date);
		}
		return;
	}

	schedule.forEach((row) => {
		row.due_date = date;
		kisan_customization.delivery_payment_days.set_row_amounts(row, totals);
	});
	frm.refresh_field("payment_schedule");

	if (frm.fields_dict.due_date) {
		frm.set_value("due_date", date);
	}
};

kisan_customization.delivery_payment_days.apply_all = function (frm) {
	if (frm.doc.custom_delivery_days) {
		kisan_customization.delivery_payment_days.apply_delivery_days(frm);
	}
	if (frm.doc.custom_payment_days) {
		kisan_customization.delivery_payment_days.apply_payment_days(frm);
	} else {
		kisan_customization.delivery_payment_days.sync_payment_amounts(frm);
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
		grand_total(frm) {
			kisan_customization.delivery_payment_days.sync_payment_amounts(frm);
		},
		rounded_total(frm) {
			kisan_customization.delivery_payment_days.sync_payment_amounts(frm);
		},
		base_grand_total(frm) {
			kisan_customization.delivery_payment_days.sync_payment_amounts(frm);
		},
		validate(frm) {
			kisan_customization.delivery_payment_days.sync_payment_amounts(frm);
		},
	};

	if (doctype === "Purchase Order") {
		handlers.transaction_date = function (frm) {
			kisan_customization.delivery_payment_days.apply_all(frm);
		};
	}

	if (doctype === "Purchase Invoice") {
		handlers.posting_date = function (frm) {
			kisan_customization.delivery_payment_days.apply_payment_days(frm);
		};
		handlers.bill_date = function (frm) {
			kisan_customization.delivery_payment_days.apply_payment_days(frm);
		};
		handlers.onload = function (frm) {
			if (frm.doc.custom_payment_days) {
				kisan_customization.delivery_payment_days.apply_payment_days(frm);
			}
		};
	}

	frappe.ui.form.on(doctype, handlers);
};
