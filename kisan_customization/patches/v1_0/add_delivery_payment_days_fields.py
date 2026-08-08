# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
		{
			"fieldname": "custom_delivery_days",
			"fieldtype": "Int",
			"insert_after": "transaction_date",
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

	from kisan_customization.patches.v1_0.fix_custom_field_layout import (
		_set_schedule_date_after_payment_days,
	)

	_set_schedule_date_after_payment_days()
	frappe.clear_cache(doctype="Purchase Order")
