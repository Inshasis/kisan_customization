# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	if frappe.db.exists("DocType", "Broker Commission"):
		frappe.db.set_value(
			"DocField",
			{"parent": "Broker Commission", "fieldname": "purchase_invoice"},
			"reqd",
			0,
		)

	if not frappe.db.exists("DocField", {"parent": "Broker Commission", "fieldname": "sales_invoice"}):
		doc = frappe.get_doc("DocType", "Broker Commission")
		doc.append(
			"fields",
			{
				"fieldname": "sales_invoice",
				"fieldtype": "Link",
				"label": "Sales Invoice",
				"options": "Sales Invoice",
				"read_only": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
				"insert_after": "purchase_invoice",
			},
		)
		doc.save()

	frappe.clear_cache(doctype="Broker Commission")
