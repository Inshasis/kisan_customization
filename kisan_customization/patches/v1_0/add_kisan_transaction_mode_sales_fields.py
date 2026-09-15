# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Sales Order": [
		{
			"fieldname": "custom_kisan_transaction_mode",
			"fieldtype": "Select",
			"insert_after": "company",
			"label": "Transaction Mode",
			"options": "Regular\nKisan Custom",
			"default": "Kisan Custom",
			"read_only": 0,
			"in_standard_filter": 1,
			"no_copy": 0,
		},
	],
	"Sales Invoice": [
		{
			"fieldname": "custom_kisan_transaction_mode",
			"fieldtype": "Select",
			"insert_after": "company",
			"label": "Transaction Mode",
			"options": "Regular\nKisan Custom",
			"default": "Kisan Custom",
			"read_only": 0,
			"in_standard_filter": 1,
			"no_copy": 0,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Sales Order")
	frappe.clear_cache(doctype="Sales Invoice")
