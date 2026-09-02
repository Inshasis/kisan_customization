# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

COLUMN_BREAKS_TO_REMOVE = (
	"custom_weight_column_break_1",
	"custom_weight_column_break_2",
	"custom_weight_column_break_3",
	"custom_weight_column_break_4",
	"custom_weight_column_break_5",
	"custom_column_break_weight_1",
	"custom_column_break_weight_2",
)

WEIGHT_FIELD_ORDER = (
	("custom_total_bags", "custom_weight_info_section"),
	("custom_total_gross_weight", "custom_total_bags"),
	("custom_total_arrival_weight", "custom_total_gross_weight"),
	("custom_weight_deduction", "custom_total_arrival_weight"),
	("custom_bag_deduction", "custom_weight_deduction"),
	("custom_bag_deduction_amount", "custom_bag_deduction"),
	("custom_weight_deduction_amount", "custom_bag_deduction_amount"),
	("custom_deductions_section", "custom_weight_deduction_amount"),
)

WEIGHT_DATA_FIELDS = (
	"custom_total_bags",
	"custom_total_gross_weight",
	"custom_total_arrival_weight",
	"custom_weight_deduction",
	"custom_bag_deduction",
	"custom_bag_deduction_amount",
	"custom_weight_deduction_amount",
)


def execute():
	for fieldname in COLUMN_BREAKS_TO_REMOVE:
		_remove_custom_field(fieldname)

	for fieldname, insert_after in WEIGHT_FIELD_ORDER:
		delete_property_setter("Purchase Invoice", "insert_after", fieldname)
		_set_custom_field_insert_after(fieldname, insert_after)

	for fieldname in WEIGHT_DATA_FIELDS:
		_set_field_columns(fieldname, 3)

	frappe.clear_cache(doctype="Purchase Invoice")


def _remove_custom_field(fieldname):
	custom_field_name = f"Purchase Invoice-{fieldname}"
	if not frappe.db.exists("Custom Field", custom_field_name):
		return

	delete_property_setter("Purchase Invoice", "insert_after", fieldname)
	frappe.delete_doc("Custom Field", custom_field_name, force=1)


def _set_custom_field_insert_after(fieldname, insert_after):
	custom_field_name = f"Purchase Invoice-{fieldname}"
	if not frappe.db.exists("Custom Field", custom_field_name):
		return

	frappe.db.set_value(
		"Custom Field",
		custom_field_name,
		"insert_after",
		insert_after,
		update_modified=False,
	)


def _set_field_columns(fieldname, columns):
	custom_field_name = f"Purchase Invoice-{fieldname}"
	if frappe.db.exists("Custom Field", custom_field_name):
		frappe.db.set_value(
			"Custom Field",
			custom_field_name,
			"columns",
			columns,
			update_modified=False,
		)

	delete_property_setter("Purchase Invoice", "columns", fieldname)
	frappe.make_property_setter(
		{
			"doctype": "Purchase Invoice",
			"doctype_or_field": "DocField",
			"fieldname": fieldname,
			"property": "columns",
			"value": str(columns),
			"property_type": "Int",
		},
		validate_fields_for_doctype=False,
	)
