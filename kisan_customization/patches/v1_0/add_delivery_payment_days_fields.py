# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
		{
			"fieldname": "custom_delivery_days",
			"fieldtype": "Int",
			"insert_after": "transaction_date",
			"label": "Delivery Days",
			"non_negative": 1,
		},
		{
			"fieldname": "custom_payment_days",
			"fieldtype": "Int",
			"insert_after": "custom_delivery_days",
			"label": "Payment Days",
			"non_negative": 1,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)

	if frappe.db.exists("Custom Field", "Purchase Order-custom_payment_days"):
		frappe.make_property_setter(
			"Purchase Order",
			"schedule_date",
			"insert_after",
			"custom_payment_days",
			"Data",
			force=True,
			validate_fields_for_doctype=False,
		)

	frappe.clear_cache(doctype="Purchase Order")
