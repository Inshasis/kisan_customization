# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	frappe.db.set_value(
		"DocType",
		"Bag Configuration",
		{"title_field": "", "show_title_field_in_link": 0},
		update_modified=False,
	)

	for name in (
		"Bag Configuration-naming_series-default",
		"Bag Configuration-naming_series-options",
	):
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, force=1, ignore_permissions=True)

	frappe.clear_cache(doctype="Bag Configuration")
