# Copyright (c) 2026, Hidayatali and contributors
"""Export Kisan custom fields to module `custom/` for bench migrate sync.

Usage:
  bench --site SITE set-config developer_mode 1
  bench --site SITE execute kisan_customization.setup.export_customizations.run
"""

import json
import os

import frappe
from frappe.modules.utils import get_module_path, scrub

MODULE = "Kisan Customization"

EXPORT_DOCTYPES = (
	"Purchase Invoice",
	"Purchase Invoice Item",
	"Purchase Order",
	"Sales Invoice",
	"Sales Order",
)


def run():
	if not frappe.conf.get("developer_mode"):
		frappe.throw("Enable developer_mode on the site before exporting customizations.")

	exported = []
	for doctype in EXPORT_DOCTYPES:
		path = export_kisan_doctype_customizations(doctype)
		if path:
			exported.append((doctype, path))

	return exported


def export_kisan_doctype_customizations(doctype):
	custom_fields = frappe.get_all(
		"Custom Field",
		fields="*",
		filters={"dt": doctype, "fieldname": ("like", "custom_%")},
		order_by="idx asc, name asc",
	)
	if not custom_fields:
		return None

	for row in custom_fields:
		row["module"] = MODULE

	payload = {
		"custom_fields": custom_fields,
		"property_setters": [],
		"custom_perms": [],
		"links": [],
		"doctype": doctype,
		"sync_on_migrate": 1,
	}

	folder_path = os.path.join(get_module_path(MODULE), "custom")
	os.makedirs(folder_path, exist_ok=True)
	path = os.path.join(folder_path, scrub(doctype) + ".json")

	with open(path, "w", encoding="utf-8") as handle:
		handle.write(frappe.as_json(payload, indent=1))

	return path
