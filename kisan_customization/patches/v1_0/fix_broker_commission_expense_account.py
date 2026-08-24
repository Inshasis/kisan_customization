# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	custom_field_name = "Kisan Master Settings-broker_commission_expense_account"

	if frappe.db.exists("Custom Field", custom_field_name):
		frappe.delete_doc("Custom Field", custom_field_name, force=1)

	if not frappe.db.exists(
		"DocField",
		{"parent": "Kisan Master Settings", "fieldname": "broker_commission_expense_account"},
	):
		frappe.throw(
			"broker_commission_expense_account is missing from Kisan Master Settings DocType. "
			"Run bench migrate and ensure kisan_customization is updated."
		)

	frappe.clear_cache(doctype="Kisan Master Settings")
