# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SALES_INVOICE_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "custom_delivery_days",
			"fieldtype": "Int",
			"insert_after": "posting_date",
			"label": "Delivery Days",
			"non_negative": 1,
		},
		{
			"fieldname": "custom_payment_days",
			"fieldtype": "Int",
			"insert_after": "custom_delivery_days",
			"label": "Payment Days",
			"non_negative": 1,
			"read_only": 0,
		},
		{
			"fieldname": "custom_delivery_date",
			"fieldtype": "Date",
			"insert_after": "custom_payment_days",
			"label": "Delivery Date",
		},
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
			"read_only": 0,
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
			"read_only": 0,
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
			"read_only": 0,
		},
		{
			"fieldname": "custom_commission_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_commission_percent",
			"label": "Commission Amount",
			"read_only": 0,
		},
		{
			"fieldname": "custom_broker_commission_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_commission_amount",
			"label": "Broker Commission Amount",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(SALES_INVOICE_FIELDS, update=True)
	_set_due_date_after_delivery_date()
	frappe.clear_cache(doctype="Sales Invoice")


def _set_due_date_after_delivery_date():
	if not frappe.db.exists("Custom Field", "Sales Invoice-custom_delivery_date"):
		return

	from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

	delete_property_setter("Sales Invoice", "insert_after", "due_date")
	frappe.make_property_setter(
		{
			"doctype": "Sales Invoice",
			"doctype_or_field": "DocField",
			"fieldname": "due_date",
			"property": "insert_after",
			"value": "custom_delivery_date",
			"property_type": "Data",
		},
		validate_fields_for_doctype=False,
	)
