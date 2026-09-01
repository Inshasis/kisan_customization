# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	for fieldname in ("custom_sauda_qty_from", "custom_sauda_qty_to"):
		custom_field = f"Purchase Order Item-{fieldname}"
		if frappe.db.exists("Custom Field", custom_field):
			frappe.delete_doc("Custom Field", custom_field, force=1)

	frappe.clear_cache(doctype="Purchase Order Item")
