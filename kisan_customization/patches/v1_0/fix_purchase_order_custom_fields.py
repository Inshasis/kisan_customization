# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from kisan_customization.patches.v1_0.fix_custom_field_layout import (
	PURCHASE_ORDER_FIELDS,
	_set_schedule_date_after_payment_days,
)


def execute():
	create_custom_fields(PURCHASE_ORDER_FIELDS, update=True)
	_set_schedule_date_after_payment_days()
	frappe.clear_cache(doctype="Purchase Order")
