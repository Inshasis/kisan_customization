# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
		{
			"fieldname": "custom_section_break_lqipi",
			"fieldtype": "Section Break",
			"insert_after": "base_tax_withholding_net_total",
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
		{
			"fieldname": "custom_delivery_days",
			"fieldtype": "Int",
			"insert_after": "custom_broker_commission_amount",
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
	frappe.clear_cache(doctype="Purchase Order")
