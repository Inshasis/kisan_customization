# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	_rename_slash_names()
	frappe.clear_cache(doctype="Bag Configuration")


def _rename_slash_names():
	for row in frappe.get_all("Bag Configuration", pluck="name"):
		if not row or "/" not in row:
			continue

		new_name = row.replace("/", "-")
		if new_name == row or frappe.db.exists("Bag Configuration", new_name):
			continue

		frappe.rename_doc("Bag Configuration", row, new_name, force=True, merge=False)
