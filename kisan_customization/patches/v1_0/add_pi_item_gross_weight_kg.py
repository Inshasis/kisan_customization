# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Purchase Invoice Item": [
				{
					"fieldname": "custom_gross_weight_kg",
					"fieldtype": "Float",
					"insert_after": "qty",
					"label": "Gross Weight (Kg)",
					"precision": 2,
					"read_only": 0,
					"in_list_view": 1,
					"depends_on": "eval:parent.custom_kisan_transaction_mode=='Kisan Custom' && !parent.is_return",
				}
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="Purchase Invoice Item")
