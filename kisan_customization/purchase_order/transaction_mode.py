# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.utils.transaction_mode import MODE_FIELD


@frappe.whitelist()
def get_purchase_order_transaction_mode(purchase_order):
	if not purchase_order or not frappe.db.exists("Purchase Order", purchase_order):
		return None

	return frappe.db.get_value("Purchase Order", purchase_order, MODE_FIELD)
