frappe.provide("kisan_customization.transaction_mode");

kisan_customization.transaction_mode.MODE_REGULAR = "Regular";
kisan_customization.transaction_mode.MODE_KISAN = "Kisan Custom";
kisan_customization.transaction_mode.FIELD = "custom_kisan_transaction_mode";
kisan_customization.transaction_mode.USER_DEFAULT_KEY = "kisan_default_transaction_mode";

kisan_customization.transaction_mode.is_kisan_custom = function (frm) {
	if (frm.doc.is_return) {
		return true;
	}

	const mode = frm.doc[kisan_customization.transaction_mode.FIELD];
	if (mode) {
		return mode === kisan_customization.transaction_mode.MODE_KISAN;
	}

	// Mode not set yet on a new document — treat as Kisan until chosen/inherited.
	return true;
};

kisan_customization.transaction_mode.get_source_purchase_order = function (frm) {
	if (frm.doctype !== "Purchase Invoice") {
		return null;
	}

	for (const row of frm.doc.items || []) {
		if (row.purchase_order) {
			return row.purchase_order;
		}
	}

	return null;
};

kisan_customization.transaction_mode.get_source_sales_order = function (frm) {
	if (frm.doctype !== "Sales Invoice") {
		return null;
	}

	for (const row of frm.doc.items || []) {
		if (row.sales_order) {
			return row.sales_order;
		}
	}

	return null;
};

kisan_customization.transaction_mode.get_source_order = function (frm) {
	return (
		kisan_customization.transaction_mode.get_source_purchase_order(frm) ||
		kisan_customization.transaction_mode.get_source_sales_order(frm)
	);
};

kisan_customization.transaction_mode.inherit_mode_from_purchase_order = function (frm) {
	const po_name = kisan_customization.transaction_mode.get_source_purchase_order(frm);
	if (!po_name) {
		return Promise.resolve(false);
	}

	return frappe
		.xcall(
			"kisan_customization.purchase_order.transaction_mode.get_purchase_order_transaction_mode",
			{ purchase_order: po_name }
		)
		.then((mode) => {
			if (!mode) {
				return false;
			}
			return frm.set_value(kisan_customization.transaction_mode.FIELD, mode).then(() => true);
		})
		.catch(() => false);
};

kisan_customization.transaction_mode.inherit_mode_from_sales_order = function (frm) {
	const so_name = kisan_customization.transaction_mode.get_source_sales_order(frm);
	if (!so_name) {
		return Promise.resolve(false);
	}

	return frappe
		.xcall(
			"kisan_customization.sales_order.transaction_mode.get_sales_order_transaction_mode",
			{ sales_order: so_name }
		)
		.then((mode) => {
			if (!mode) {
				return false;
			}
			return frm.set_value(kisan_customization.transaction_mode.FIELD, mode).then(() => true);
		})
		.catch(() => false);
};

kisan_customization.transaction_mode.inherit_mode_from_source_order = function (frm) {
	if (kisan_customization.transaction_mode.get_source_purchase_order(frm)) {
		return kisan_customization.transaction_mode.inherit_mode_from_purchase_order(frm);
	}
	if (kisan_customization.transaction_mode.get_source_sales_order(frm)) {
		return kisan_customization.transaction_mode.inherit_mode_from_sales_order(frm);
	}
	return Promise.resolve(false);
};

kisan_customization.transaction_mode.get_kisan_fieldnames = function (frm) {
	const fieldnames = new Set();
	const mode_field = kisan_customization.transaction_mode.FIELD;

	(frm.meta?.fields || []).forEach((df) => {
		if (df.fieldname?.startsWith("custom_") && df.fieldname !== mode_field) {
			fieldnames.add(df.fieldname);
		}
	});

	Object.keys(frm.fields_dict || {}).forEach((fieldname) => {
		if (fieldname.startsWith("custom_") && fieldname !== mode_field) {
			fieldnames.add(fieldname);
		}
	});

	return [...fieldnames];
};

kisan_customization.transaction_mode.toggle_ui = function (frm) {
	const mode_field = kisan_customization.transaction_mode.FIELD;
	if (frm.fields_dict[mode_field]) {
		const read_only = !frm.is_new() || frm.doc.docstatus === 1;
		frm.set_df_property(mode_field, "read_only", read_only ? 1 : 0);
	}

	let show_kisan = kisan_customization.transaction_mode.is_kisan_custom(frm);
	// Return / debit note PI: keep Kisan server logic but hide trading sections on the form.
	if (frm.doctype === "Purchase Invoice" && cint(frm.doc.is_return)) {
		show_kisan = false;
	}

	kisan_customization.transaction_mode.get_kisan_fieldnames(frm).forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.toggle_display(fieldname, show_kisan);
		}
		frm.set_df_property(fieldname, "hidden", show_kisan ? 0 : 1);
	});

	if (frm.fields_dict.custom_supplier_invoice_amount) {
		frm.toggle_reqd("custom_supplier_invoice_amount", show_kisan && !frm.doc.is_return);
	}
};

kisan_customization.transaction_mode.sync_ui_visibility = function (frm) {
	const sync = () => {
		kisan_customization.transaction_mode.toggle_ui(frm);
		if (
			frm.doctype === "Purchase Invoice" &&
			kisan_customization.purchase_invoice?.apply_return_layout
		) {
			kisan_customization.purchase_invoice.apply_return_layout(frm);
		}
	};
	sync();
	frappe.after_ajax(sync);
	setTimeout(sync, 100);
	setTimeout(sync, 350);
};

kisan_customization.transaction_mode.apply_mode_side_effects = function (frm) {
	kisan_customization.transaction_mode.sync_ui_visibility(frm);
	frm.trigger("kisan_transaction_mode_set");
};

kisan_customization.transaction_mode.show_mode_dialog = function (frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Transaction Type"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "mode",
				label: __("How do you want to use this document?"),
				options: [
					kisan_customization.transaction_mode.MODE_REGULAR,
					kisan_customization.transaction_mode.MODE_KISAN,
				].join("\n"),
				default: kisan_customization.transaction_mode.MODE_KISAN,
				reqd: 1,
			},
			{
				fieldtype: "Check",
				fieldname: "remember",
				label: __("Remember my choice for new documents"),
			},
			{
				fieldtype: "Small Text",
				fieldname: "help",
				read_only: 1,
				default: __(
					"Regular: standard ERPNext only. Kisan Custom: broker, payment/delivery terms, and related Kisan validations."
				),
			},
		],
		primary_action_label: __("Continue"),
		primary_action(values) {
			frm.set_value(kisan_customization.transaction_mode.FIELD, values.mode).then(() => {
				if (values.remember) {
					frappe.call({
						method: "frappe.client.set_user_default",
						args: {
							key: kisan_customization.transaction_mode.USER_DEFAULT_KEY,
							value: values.mode,
						},
					});
				}
				kisan_customization.transaction_mode.apply_mode_side_effects(frm);
			});
			dialog.hide();
		},
	});

	dialog.show();
};

kisan_customization.transaction_mode.prompt_or_default = function (frm) {
	if (frm._kisan_mode_prompted) {
		return;
	}
	frm._kisan_mode_prompted = true;

	if (kisan_customization.transaction_mode.get_source_order(frm)) {
		kisan_customization.transaction_mode
			.inherit_mode_from_source_order(frm)
			.then((inherited) => {
				if (inherited) {
					kisan_customization.transaction_mode.apply_mode_side_effects(frm);
					return;
				}
				kisan_customization.transaction_mode.show_mode_dialog(frm);
			});
		return;
	}

	const saved_default = frappe.defaults.get_user_default(
		kisan_customization.transaction_mode.USER_DEFAULT_KEY
	);
	if (saved_default) {
		frm
			.set_value(kisan_customization.transaction_mode.FIELD, saved_default)
			.then(() => kisan_customization.transaction_mode.apply_mode_side_effects(frm));
		return;
	}

	kisan_customization.transaction_mode.show_mode_dialog(frm);
};

kisan_customization.transaction_mode.init_document_mode = function (frm) {
	if (!frm.is_new() || frm.doc.is_return) {
		kisan_customization.transaction_mode.sync_ui_visibility(frm);
		return Promise.resolve();
	}

	if (frm.doc[kisan_customization.transaction_mode.FIELD]) {
		kisan_customization.transaction_mode.apply_mode_side_effects(frm);
		return Promise.resolve();
	}

	return kisan_customization.transaction_mode
		.inherit_mode_from_source_order(frm)
		.then((inherited) => {
			if (inherited || frm.doc[kisan_customization.transaction_mode.FIELD]) {
				kisan_customization.transaction_mode.apply_mode_side_effects(frm);
				return;
			}
			kisan_customization.transaction_mode.prompt_or_default(frm);
		});
};

kisan_customization.transaction_mode.bind = function (doctype) {
	frappe.ui.form.on(doctype, {
		onload(frm) {
			kisan_customization.transaction_mode.init_document_mode(frm);
		},

		refresh(frm) {
			if (
				frm.is_new() &&
				!frm.doc.is_return &&
				!frm.doc[kisan_customization.transaction_mode.FIELD] &&
				kisan_customization.transaction_mode.get_source_order(frm)
			) {
				kisan_customization.transaction_mode
					.inherit_mode_from_source_order(frm)
					.then(() => {
						kisan_customization.transaction_mode.apply_mode_side_effects(frm);
					});
				return;
			}
			kisan_customization.transaction_mode.sync_ui_visibility(frm);
		},

		[kisan_customization.transaction_mode.FIELD](frm) {
			kisan_customization.transaction_mode.apply_mode_side_effects(frm);
		},
	});

	const invoice_item_handlers = {
		items_add(frm) {
			if (
				!frm.is_new() ||
				frm.doc[kisan_customization.transaction_mode.FIELD] ||
				!kisan_customization.transaction_mode.get_source_order(frm)
			) {
				return;
			}
			kisan_customization.transaction_mode
				.inherit_mode_from_source_order(frm)
				.then((inherited) => {
					if (inherited) {
						kisan_customization.transaction_mode.apply_mode_side_effects(frm);
					}
				});
		},
	};

	if (doctype === "Purchase Invoice") {
		frappe.ui.form.on("Purchase Invoice Item", invoice_item_handlers);
	}
	if (doctype === "Sales Invoice") {
		frappe.ui.form.on("Sales Invoice Item", invoice_item_handlers);
	}
};

kisan_customization.transaction_mode.bind("Purchase Order");
kisan_customization.transaction_mode.bind("Purchase Invoice");
kisan_customization.transaction_mode.bind("Sales Order");
kisan_customization.transaction_mode.bind("Sales Invoice");
