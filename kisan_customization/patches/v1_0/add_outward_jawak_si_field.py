# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "custom_outward_jawak",
			"fieldtype": "Link",
			"insert_after": "customer",
			"label": "Outward Jawak",
			"options": "Outward Jawak",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Sales Invoice")
