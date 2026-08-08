# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from kisan_customization.patches.v1_0.fix_custom_field_layout import PURCHASE_INVOICE_FIELDS

PI_BROKER_READ_ONLY_FIELDS = (
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
	"custom_broker_commission_amount",
)

PI_TOTAL_FIELD_ORDER = (
	("total_qty", "custom_total_arrival_weight"),
	("column_break_28", "total_qty"),
	("total", "column_break_28"),
	("net_total", "total"),
	("base_total", "section_break_26"),
	("base_net_total", "base_total"),
)


def execute():
	_remove_pi_broker_column_break()
	create_custom_fields(PURCHASE_INVOICE_FIELDS, update=True)
	_set_pi_broker_fields_read_only()
	_set_pi_total_qty_layout()
	frappe.clear_cache(doctype="Purchase Invoice")


def _remove_pi_broker_column_break():
	fieldname = "Purchase Invoice-custom_column_break_y5zpm"
	if frappe.db.exists("Custom Field", fieldname):
		frappe.delete_doc("Custom Field", fieldname, force=1)


def _set_pi_broker_fields_read_only():
	for fieldname in PI_BROKER_READ_ONLY_FIELDS:
		custom_field = f"Purchase Invoice-{fieldname}"
		if frappe.db.exists("Custom Field", custom_field):
			frappe.db.set_value("Custom Field", custom_field, "read_only", 1)


def _set_pi_total_qty_layout():
	from frappe.custom.doctype.property_setter.property_setter import delete_property_setter

	for fieldname, insert_after in PI_TOTAL_FIELD_ORDER:
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
