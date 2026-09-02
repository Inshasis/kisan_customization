# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_bag_deduction",
			"fieldtype": "Float",
			"insert_after": "custom_total_arrival_weight",
			"label": "Bag Deduction (kg)",
			"precision": "2",
			"read_only": 1,
		},
		{
			"fieldname": "custom_bag_deduction_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_bag_deduction",
			"label": "Bag Deduction Amount",
			"read_only": 1,
		},
		{
			"fieldname": "custom_weight_deduction_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_weight_deduction",
			"label": "Weight Deduction Amount",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Invoice")
