# Copyright (c) 2026, Hidayatali and contributors

import frappe

READ_ONLY_PERMISSIONS = [
	{
		"role": "Accounts User",
		"read": 1,
		"report": 1,
		"export": 1,
		"print": 1,
		"email": 1,
	},
	{
		"role": "Accounts Manager",
		"read": 1,
		"report": 1,
		"export": 1,
		"print": 1,
		"email": 1,
	},
	{
		"role": "System Manager",
		"read": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
]


def execute():
	frappe.db.delete("DocPerm", {"parent": "Broker Commission"})

	for perm in READ_ONLY_PERMISSIONS:
		frappe.get_doc(
			{
				"doctype": "DocPerm",
				"parent": "Broker Commission",
				"parenttype": "DocType",
				"parentfield": "permissions",
				**perm,
			}
		).insert(ignore_permissions=True)

	frappe.db.set_value("DocType", "Broker Commission", "in_create", 1, update_modified=False)
	frappe.clear_cache(doctype="Broker Commission")
	frappe.db.commit()
