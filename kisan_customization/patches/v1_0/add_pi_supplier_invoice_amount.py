# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_supplier_invoice_amount",
			"fieldtype": "Currency",
			"insert_after": "bill_date",
			"label": "Supplier Invoice Amount",
			"options": "Company:company:default_currency",
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Invoice")
