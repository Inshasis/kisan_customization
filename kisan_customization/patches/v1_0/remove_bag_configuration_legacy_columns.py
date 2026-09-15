# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	_drop_legacy_bag_configuration_columns()
	_allow_null_weight_kg()
	frappe.clear_cache(doctype="Bag Configuration")


def _drop_legacy_bag_configuration_columns():
	table = "tabBag Configuration"

	if not frappe.db.table_exists("Bag Configuration"):
		return

	for column in ("bag_weight", "rate_per_bag_per_day", "naming_series"):
		if not frappe.db.has_column("Bag Configuration", column):
			continue

		_drop_column_indexes(table, column)
		frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `{column}`")


def _drop_column_indexes(table, column):
	indexes = frappe.db.sql(
		f"""
		SHOW INDEX FROM `{table}`
		WHERE Column_name = %s AND Key_name != 'PRIMARY'
		""",
		column,
		as_dict=True,
	)

	seen = set()
	for row in indexes:
		key = row.get("Key_name")
		if not key or key in seen:
			continue
		seen.add(key)
		frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP INDEX `{key}`")


def _allow_null_weight_kg():
	if not frappe.db.has_column("Bag Configuration", "weight_kg"):
		return

	frappe.db.sql_ddl(
		"""
		ALTER TABLE `tabBag Configuration`
		MODIFY COLUMN weight_kg int(11) NULL DEFAULT NULL
		"""
	)
