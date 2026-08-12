# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
		{
			"fieldname": "custom_aggregator_booking",
			"fieldtype": "Link",
			"insert_after": "supplier",
			"label": "Aggregator Booking",
			"options": "Aggregator Booking",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Order")
