# Copyright (c) 2026, Hidayatali and contributors

import frappe

MODE_FIELD = "custom_kisan_transaction_mode"
PARENT_DEPENDS = f"eval:doc.{MODE_FIELD}=='Kisan Custom' && !doc.is_return"


def execute():
	for doctype in ("Purchase Invoice", "Purchase Order", "Sales Invoice", "Sales Order"):
		_set_depends_on(doctype)

	frappe.clear_cache()


def _set_depends_on(doctype):
	for row in frappe.get_all(
		"Custom Field",
		filters={"dt": doctype, "fieldname": ("like", "custom_%")},
		fields=["name", "fieldname", "fieldtype"],
	):
		if row.fieldname == MODE_FIELD:
			continue

		depends_on = PARENT_DEPENDS
		if doctype in ("Purchase Invoice", "Sales Invoice") and row.fieldtype == "Table":
			depends_on = (
				f"eval:parent.{MODE_FIELD}=='Kisan Custom' && !parent.is_return"
			)

		frappe.db.set_value(
			"Custom Field",
			row.name,
			"depends_on",
			depends_on,
			update_modified=False,
		)
