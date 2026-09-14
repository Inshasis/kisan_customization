# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

# items → bag → weight → deductions → totals (qty | total) → broker → taxes
PI_LAYOUT_FIELD_ORDER = (
	("custom_deductions", "custom_deductions_section"),
	("total_qty", "custom_deductions"),
	("column_break_28", "total_qty"),
	("total", "column_break_28"),
	("net_total", "total"),
	("total_net_weight", "net_total"),
	("column_break_50", "total_net_weight"),
	("base_total", "column_break_50"),
	("base_net_total", "base_total"),
	("custom_section_break_lqipi", "base_net_total"),
	("custom_broker", "custom_section_break_lqipi"),
	("custom_column_break_1ked0", "custom_broker"),
	("custom_commission_type", "custom_column_break_1ked0"),
	("custom_commission_percent", "custom_commission_type"),
	("custom_commission_amount", "custom_commission_percent"),
	("custom_broker_commission_amount", "custom_commission_amount"),
	("taxes_section", "custom_broker_commission_amount"),
)

PI_TOTAL_ROW_COLUMNS = (
	("total_qty", 3),
	("total", 3),
)


def execute():
	for fieldname, insert_after in PI_LAYOUT_FIELD_ORDER:
		_set_insert_after(fieldname, insert_after)

	for fieldname, columns in PI_TOTAL_ROW_COLUMNS:
		_set_columns(fieldname, columns)

	_update_custom_field_insert_after(
		"Purchase Invoice-custom_section_break_lqipi", "base_net_total"
	)
	_update_custom_field_insert_after("Purchase Invoice-custom_broker", "custom_section_break_lqipi")

	frappe.clear_cache(doctype="Purchase Invoice")


def _set_insert_after(fieldname, insert_after):
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


def _set_columns(fieldname, columns):
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


def _update_custom_field_insert_after(custom_field_name, insert_after):
	if frappe.db.exists("Custom Field", custom_field_name):
		frappe.db.set_value(
			"Custom Field",
			custom_field_name,
			"insert_after",
			insert_after,
			update_modified=False,
		)
