# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
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
	"Purchase Invoice": [
		{
			"fieldname": "custom_section_break_delivery_payment",
			"fieldtype": "Section Break",
			"insert_after": "due_date",
			"label": "Delivery & Payment Days",
		},
		{
			"fieldname": "custom_delivery_days",
			"fieldtype": "Int",
			"insert_after": "custom_section_break_delivery_payment",
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
		{
			"fieldname": "custom_required_by",
			"fieldtype": "Date",
			"insert_after": "custom_payment_days",
			"label": "Required By",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Order")
	frappe.clear_cache(doctype="Purchase Invoice")
