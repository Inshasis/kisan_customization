# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Order": [
		{
			"fieldname": "custom_sauda_qty_from",
			"fieldtype": "Float",
			"insert_after": "is_subcontracted",
			"label": "Sauda Qty From",
			"non_negative": 1,
		},
		{
			"fieldname": "custom_sauda_qty_to",
			"fieldtype": "Float",
			"insert_after": "custom_sauda_qty_from",
			"label": "Sauda Qty To",
			"non_negative": 1,
		},
	],
}


def execute():
	section_field = "Purchase Order-custom_sauda_qty_section"
	if frappe.db.exists("Custom Field", section_field):
		frappe.delete_doc("Custom Field", section_field, force=1)

	create_custom_fields(CUSTOM_FIELDS, update=True)
	frappe.clear_cache(doctype="Purchase Order")
