# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Kisan Master Settings": [
		{
			"fieldname": "broker_commission_expense_account",
			"fieldtype": "Link",
			"insert_after": "broker_commission",
			"label": "Broker Commission Expense Account",
			"options": "Account",
		},
	],
}


def execute():
	if _field_exists("Kisan Master Settings", "broker_commission_expense_account"):
		return

	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Kisan Master Settings")


def _field_exists(doctype, fieldname):
	if frappe.db.exists("Custom Field", f"{doctype}-{fieldname}"):
		return True

	return frappe.db.exists("DocField", {"parent": doctype, "fieldname": fieldname})
