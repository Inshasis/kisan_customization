# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_weight_deduction",
			"fieldtype": "Float",
			"insert_after": "custom_total_arrival_weight",
			"label": "Weight Deduction (kg)",
			"precision": "2",
			"read_only": 1,
		},
		{
			"fieldname": "custom_deductions_section",
			"fieldtype": "Section Break",
			"insert_after": "custom_weight_deduction",
			"label": "Deductions",
		},
		{
			"fieldname": "custom_deductions",
			"fieldtype": "Table",
			"insert_after": "custom_deductions_section",
			"label": "Deduction Details",
			"options": "Purchase Invoice Deduction",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Invoice")
