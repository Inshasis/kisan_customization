# Copyright (c) 2026, Hidayatali and contributors

import frappe

PI_BROKER_EDITABLE_FIELDS = (
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
)


def execute():
	for fieldname in PI_BROKER_EDITABLE_FIELDS:
		custom_field = f"Purchase Invoice-{fieldname}"
		if frappe.db.exists("Custom Field", custom_field):
			frappe.db.set_value("Custom Field", custom_field, "read_only", 0, update_modified=False)

	if frappe.db.exists("Custom Field", "Purchase Invoice-custom_broker_commission_amount"):
		frappe.db.set_value(
			"Custom Field",
			"Purchase Invoice-custom_broker_commission_amount",
			"read_only",
			1,
			update_modified=False,
		)

	frappe.clear_cache(doctype="Purchase Invoice")
