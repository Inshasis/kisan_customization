# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PI_FIELDS_TO_REMOVE = [
	"Purchase Invoice-custom_section_break_delivery_payment",
	"Purchase Invoice-custom_delivery_days",
	"Purchase Invoice-custom_payment_days",
	"Purchase Invoice-custom_required_by",
]

PI_BROKER_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_section_break_lqipi",
			"fieldtype": "Section Break",
			"insert_after": "total_net_weight",
			"label": "Broker Commission",
		},
		{
			"fieldname": "custom_broker",
			"fieldtype": "Link",
			"insert_after": "custom_section_break_lqipi",
			"label": "Broker",
			"options": "Supplier",
		},
		{
			"fieldname": "custom_column_break_1ked0",
			"fieldtype": "Column Break",
			"insert_after": "custom_broker",
		},
		{
			"fieldname": "custom_commission_type",
			"fieldtype": "Select",
			"insert_after": "custom_column_break_1ked0",
			"label": "Commission Type",
			"options": "\nPercentage\nTotal Qty",
		},
		{
			"fieldname": "custom_column_break_y5zpm",
			"fieldtype": "Column Break",
			"insert_after": "custom_commission_type",
		},
		{
			"fieldname": "custom_commission_percent",
			"fieldtype": "Float",
			"insert_after": "custom_column_break_y5zpm",
			"label": "Commission Percent",
		},
		{
			"fieldname": "custom_commission_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_commission_percent",
			"label": "Commission Amount",
		},
		{
			"fieldname": "custom_broker_commission_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_commission_amount",
			"label": "Broker Commission Amount",
		},
	],
}


def execute():
	for fieldname in PI_FIELDS_TO_REMOVE:
		if frappe.db.exists("Custom Field", fieldname):
			frappe.delete_doc("Custom Field", fieldname, force=1)

	create_custom_fields(PI_BROKER_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Invoice")
