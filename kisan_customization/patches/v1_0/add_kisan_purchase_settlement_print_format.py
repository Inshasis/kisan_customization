# Copyright (c) 2026, Hidayatali and contributors

from pathlib import Path

import frappe

PRINT_FORMAT_NAME = "Kisan Purchase Settlement Advice"
A4_MARGINS_MM = {
	"margin_top": 8.0,
	"margin_bottom": 8.0,
	"margin_left": 8.0,
	"margin_right": 8.0,
}


def execute():
	html_path = (
		Path(frappe.get_app_path("kisan_customization"))
		/ "print_formats"
		/ "kisan_purchase_settlement_advice.html"
	)
	html = html_path.read_text(encoding="utf-8")
	values = {"html": html, **A4_MARGINS_MM}

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		frappe.db.set_value("Print Format", PRINT_FORMAT_NAME, values, update_modified=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": PRINT_FORMAT_NAME,
				"doc_type": "Purchase Invoice",
				"module": "Kisan Customization",
				"print_format_type": "Jinja",
				"standard": "No",
				"custom_format": 1,
				"disabled": 0,
				**values,
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Print Format")
