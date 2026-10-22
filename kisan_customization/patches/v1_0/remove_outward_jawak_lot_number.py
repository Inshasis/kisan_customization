# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	if not frappe.db.table_exists("Outward Jawak"):
		return
	if not frappe.db.has_column("Outward Jawak", "lot_number"):
		return

	frappe.db.sql_ddl("ALTER TABLE `tabOutward Jawak` DROP COLUMN `lot_number`")
	frappe.clear_cache(doctype="Outward Jawak")
