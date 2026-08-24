# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	if not frappe.db.exists("Custom Field", "Purchase Invoice-custom_payment_days"):
		return

	frappe.db.set_value(
		"Custom Field",
		"Purchase Invoice-custom_payment_days",
		"read_only",
		0,
		update_modified=False,
	)
	frappe.clear_cache(doctype="Purchase Invoice")
