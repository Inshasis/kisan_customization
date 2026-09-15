# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.utils.transaction_mode import MODE_FIELD, MODE_KISAN


@frappe.whitelist()
def get_sales_order_transaction_mode(sales_order):
	if not sales_order or not frappe.db.exists("Sales Order", sales_order):
		return None

	mode = frappe.db.get_value("Sales Order", sales_order, MODE_FIELD)
	return mode or MODE_KISAN
