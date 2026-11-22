# Copyright (c) 2026, Hidayatali and contributors

from pathlib import Path

import frappe

PRINT_FORMAT_NAME = "GST Sales"

PRINT_FORMAT_SETTINGS = {
	"margin_top": 2.0,
	"margin_bottom": 2.0,
	"margin_left": 0.0,
	"margin_right": 0.0,
	"font_size": 11,
	"page_number": "Hide",
}


def _html_path():
	return Path(frappe.get_app_path("kisan_customization")) / "print_formats" / "gst_sales.html"


def load_html():
	return _html_path().read_text(encoding="utf-8")


def apply_print_format():
	html = load_html()
	values = {
		"html": html,
		"doc_type": "Sales Invoice",
		"module": "Kisan Customization",
		"print_format_type": "Jinja",
		"standard": "No",
		"custom_format": 1,
		"disabled": 0,
		**PRINT_FORMAT_SETTINGS,
	}

	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		frappe.db.set_value("Print Format", PRINT_FORMAT_NAME, values, update_modified=True)
	else:
		doc = frappe.get_doc({"doctype": "Print Format", "name": PRINT_FORMAT_NAME, **values})
		doc.insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Print Format")
