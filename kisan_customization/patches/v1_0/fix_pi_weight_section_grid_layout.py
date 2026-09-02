# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

WEIGHT_GRID_FIELDS = {
	"Purchase Invoice": [
		{
			"fieldname": "custom_weight_column_break_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_total_bags",
		},
		{
			"fieldname": "custom_weight_column_break_2",
			"fieldtype": "Column Break",
			"insert_after": "custom_total_gross_weight",
		},
		{
			"fieldname": "custom_weight_column_break_3",
			"fieldtype": "Column Break",
			"insert_after": "custom_total_arrival_weight",
		},
		{
			"fieldname": "custom_weight_column_break_4",
			"fieldtype": "Column Break",
			"insert_after": "custom_bag_deduction_amount",
		},
		{
			"fieldname": "custom_weight_column_break_5",
			"fieldtype": "Column Break",
			"insert_after": "custom_weight_column_break_4",
		},
	],
}

# Row 1: Total Bags | Gross Weight | Arr. Weight | Weight Deduction (kg)
# Row 2: Bag Deduction (kg) | Bag Deduction Amount | (empty) | Weight Deduction Amount
WEIGHT_FIELD_ORDER = (
	("custom_total_bags", "custom_weight_info_section"),
	("custom_weight_column_break_1", "custom_total_bags"),
	("custom_total_gross_weight", "custom_weight_column_break_1"),
	("custom_weight_column_break_2", "custom_total_gross_weight"),
	("custom_total_arrival_weight", "custom_weight_column_break_2"),
	("custom_weight_column_break_3", "custom_total_arrival_weight"),
	("custom_weight_deduction", "custom_weight_column_break_3"),
	("custom_bag_deduction", "custom_weight_deduction"),
	("custom_bag_deduction_amount", "custom_bag_deduction"),
	("custom_weight_column_break_4", "custom_bag_deduction_amount"),
	("custom_weight_column_break_5", "custom_weight_column_break_4"),
	("custom_weight_deduction_amount", "custom_weight_column_break_5"),
	("custom_deductions_section", "custom_weight_deduction_amount"),
)


def execute():
	create_custom_fields(WEIGHT_GRID_FIELDS, update=True)

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
