# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.outward_jawak.status import (
	STATUS_CANCELLED,
	STATUS_DRAFT,
	update_outward_jawak_status,
)


def execute():
	for row in frappe.get_all("Outward Jawak", fields=["name", "docstatus"]):
		if row.docstatus == 2:
			frappe.db.set_value(
				"Outward Jawak", row.name, "status", STATUS_CANCELLED, update_modified=False
			)
		elif row.docstatus == 0:
			frappe.db.set_value(
				"Outward Jawak", row.name, "status", STATUS_DRAFT, update_modified=False
			)
		else:
			update_outward_jawak_status(row.name)

	frappe.clear_cache(doctype="Outward Jawak")
