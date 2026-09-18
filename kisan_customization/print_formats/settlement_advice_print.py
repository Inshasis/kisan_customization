# Copyright (c) 2026, Hidayatali and contributors

from pathlib import Path

import frappe

PRINT_FORMAT_NAME = "Kisan Purchase Settlement Advice"

PRINT_FORMAT_SETTINGS = {
	"margin_top": 10.0,
	"margin_bottom": 10.0,
	"margin_left": 8.0,
	"margin_right": 8.0,
	"font_size": 8,
	"page_number": "Hide",
}


def _html_path():
	return (
		Path(frappe.get_app_path("kisan_customization"))
		/ "print_formats"
		/ "kisan_purchase_settlement_advice.html"
	)


def load_html():
	return _html_path().read_text(encoding="utf-8")


def apply_print_format():
	html = load_html()
	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		frappe.db.set_value(
			"Print Format",
			PRINT_FORMAT_NAME,
			{"html": html, **PRINT_FORMAT_SETTINGS},
			update_modified=True,
		)
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
				"html": html,
				**PRINT_FORMAT_SETTINGS,
			}
		)
		doc.insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Print Format")
