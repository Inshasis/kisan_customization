# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
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
	"Purchase Invoice": [
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

	if frappe.db.exists("Custom Field", "Purchase Invoice-custom_supplier_invoice_amount"):
		frappe.db.set_value(
			"Custom Field",
			"Purchase Invoice-custom_supplier_invoice_amount",
			{
				"mandatory_depends_on": "eval:doc.custom_kisan_transaction_mode=='Kisan Custom'",
			},
		)

	frappe.clear_cache(doctype="Purchase Order")
	frappe.clear_cache(doctype="Purchase Invoice")
