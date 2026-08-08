# Copyright (c) 2026, Hidayatali and contributors

import frappe

PI_WEIGHT_SECTION_TOTAL_FIELDS = (
	("total_qty", "custom_total_arrival_weight"),
	("column_break_28", "total_qty"),
	("total", "column_break_28"),
	("net_total", "total"),
	("base_total", "section_break_26"),
	("base_net_total", "base_total"),
)


def execute():
	_move_pi_totals_to_weight_section()
	frappe.clear_cache(doctype="Purchase Invoice")


def _move_pi_totals_to_weight_section():
	from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

	for fieldname, insert_after in PI_WEIGHT_SECTION_TOTAL_FIELDS:
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
