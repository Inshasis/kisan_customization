# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PURCHASE_ORDER_FIELDS = {
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
			"read_only": 1,
		},
	],
}

PURCHASE_INVOICE_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_bag_details_section",
			"fieldtype": "Section Break",
			"insert_after": "items",
			"label": "Bag Details",
		},
		{
			"fieldname": "custom_bag_details",
			"fieldtype": "Table",
			"insert_after": "custom_bag_details_section",
			"label": "Bag Details",
			"options": "Purchase Invoice Bag Detail",
		},
		{
			"fieldname": "custom_weight_info_section",
			"fieldtype": "Section Break",
			"insert_after": "custom_bag_details",
			"label": "Weight Information",
		},
		{
			"fieldname": "custom_total_bags",
			"fieldtype": "Int",
			"insert_after": "custom_weight_info_section",
			"label": "Total Bags",
			"non_negative": 1,
		},
		{
			"fieldname": "custom_total_gross_weight",
			"fieldtype": "Float",
			"insert_after": "custom_total_bags",
			"label": "Total Gross Weight (kg)",
			"non_negative": 1,
			"precision": "2",
		},
		{
			"fieldname": "custom_total_arrival_weight",
			"fieldtype": "Float",
			"insert_after": "custom_total_gross_weight",
			"label": "Total Arr. Weight (kg)",
			"non_negative": 1,
			"precision": "2",
			"read_only": 1,
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
			"read_only": 1,
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
			"read_only": 1,
		},
		{
			"fieldname": "custom_commission_percent",
			"fieldtype": "Float",
			"insert_after": "custom_commission_type",
			"label": "Commission Percent",
			"read_only": 1,
		},
		{
			"fieldname": "custom_commission_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_commission_percent",
			"label": "Commission Amount",
			"read_only": 1,
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
	create_custom_fields(PURCHASE_ORDER_FIELDS, update=True)
	create_custom_fields(PURCHASE_INVOICE_FIELDS, update=True)
	_set_schedule_date_after_payment_days()
	frappe.clear_cache(doctype="Purchase Order")
	frappe.clear_cache(doctype="Purchase Invoice")


def _set_schedule_date_after_payment_days():
	if not frappe.db.exists("Custom Field", "Purchase Order-custom_payment_days"):
		return

	from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

	delete_property_setter("Purchase Order", "insert_after", "schedule_date")
	frappe.make_property_setter(
		{
			"doctype": "Purchase Order",
			"doctype_or_field": "DocField",
			"fieldname": "schedule_date",
			"property": "insert_after",
			"value": "custom_payment_days",
			"property_type": "Data",
		},
		validate_fields_for_doctype=False,
	)
