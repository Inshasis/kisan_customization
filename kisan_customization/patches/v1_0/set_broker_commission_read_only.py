# Copyright (c) 2026, Hidayatali and contributors

import frappe

PI_BROKER_READ_ONLY_FIELDS = (
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
	"custom_broker_commission_amount",
)


def execute():
	for fieldname in PI_BROKER_READ_ONLY_FIELDS:
		custom_field = f"Purchase Invoice-{fieldname}"
		if frappe.db.exists("Custom Field", custom_field):
			frappe.db.set_value("Custom Field", custom_field, "read_only", 1)

	frappe.clear_cache(doctype="Purchase Order")
	frappe.clear_cache(doctype="Purchase Invoice")
