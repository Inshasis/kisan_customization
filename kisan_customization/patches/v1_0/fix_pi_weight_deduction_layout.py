# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

WEIGHT_FIELD_ORDER = (
	("custom_bag_deduction", "custom_total_arrival_weight"),
	("custom_bag_deduction_amount", "custom_bag_deduction"),
	("custom_weight_deduction", "custom_bag_deduction_amount"),
	("custom_weight_deduction_amount", "custom_weight_deduction"),
	("custom_deductions_section", "custom_weight_deduction_amount"),
)

ENSURE_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_weight_deduction_amount",
			"fieldtype": "Currency",
			"insert_after": "custom_weight_deduction",
			"label": "Weight Deduction Amount",
			"read_only": 1,
		},
	],
}


def execute():
	create_custom_fields(ENSURE_FIELDS, update=True)

	for fieldname, insert_after in WEIGHT_FIELD_ORDER:
		_set_insert_after(fieldname, insert_after)

	frappe.clear_cache(doctype="Purchase Invoice")


def _set_insert_after(fieldname, insert_after):
	custom_field_name = f"Purchase Invoice-{fieldname}"
	if frappe.db.exists("Custom Field", custom_field_name):
		frappe.db.set_value(
			"Custom Field",
			custom_field_name,
			"insert_after",
			insert_after,
			update_modified=False,
		)

	from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

	delete_property_setter("Purchase Invoice", "insert_after", fieldname)
	frappe.make_property_setter(
		{
			"doctype": "Purchase Invoice",
			"doctype_or_field": "DocField",
			"fieldname": fieldname,
			"property": "insert_after",
			"value": insert_after,
			"property_type": "Data",
		},
		validate_fields_for_doctype=False,
	)
