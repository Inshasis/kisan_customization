# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	fieldname = "Sales Invoice-custom_outward_jawak"
	if frappe.db.exists("Custom Field", fieldname):
		frappe.delete_doc("Custom Field", fieldname, force=1)

	frappe.clear_cache(doctype="Sales Invoice")
