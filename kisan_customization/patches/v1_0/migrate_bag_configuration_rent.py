# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import cint


def execute():
	_migrate_bag_configuration_columns()
	_seed_specific_master_settings()
	_backfill_bag_configuration_links()
	frappe.clear_cache(doctype="Bag Configuration")
	frappe.clear_cache(doctype="Bag Details")
	frappe.clear_cache(doctype="Jawak Bag Detail")
	frappe.clear_cache(doctype="Kisan Master Settings")


def _migrate_bag_configuration_columns():
	table = "tabBag Configuration"

	if frappe.db.has_column("Bag Configuration", "bag_weight") and frappe.db.has_column(
		"Bag Configuration", "weight_kg"
	):
		frappe.db.sql(
			f"""
			UPDATE `{table}`
			SET weight_kg = bag_weight
			WHERE (weight_kg IS NULL OR weight_kg = 0) AND bag_weight IS NOT NULL
			"""
		)

	if frappe.db.has_column("Bag Configuration", "rate_per_bag_per_day") and frappe.db.has_column(
		"Bag Configuration", "rate"
	):
		frappe.db.sql(
			f"""
			UPDATE `{table}`
			SET rate = rate_per_bag_per_day
			WHERE (rate IS NULL OR rate = 0) AND rate_per_bag_per_day IS NOT NULL
			"""
		)

	if frappe.db.has_column("Bag Configuration", "rate_type"):
		frappe.db.sql(
			f"""
			UPDATE `{table}`
			SET rate_type = 'General'
			WHERE rate_type IS NULL OR rate_type = ''
			"""
		)

	if frappe.db.has_column("Bag Configuration", "uom"):
		frappe.db.sql(
			f"""
			UPDATE `{table}`
			SET uom = 'Bag'
			WHERE uom IS NULL OR uom = ''
			"""
		)

	if frappe.db.has_column("Bag Configuration", "naming_series"):
		frappe.db.sql(
			f"""
			UPDATE `{table}`
			SET naming_series = 'BC-.#####'
			WHERE naming_series IS NULL OR naming_series = ''
			"""
		)


def _seed_specific_master_settings():
	settings = frappe.get_single("Kisan Master Settings")
	changed = False

	for fieldname, value in (
		("specific_minimum_days", 30),
		("specific_extra_days", 2),
		("specific_days_per_month", 30),
	):
		if settings.meta.has_field(fieldname) and not settings.get(fieldname):
			settings.set(fieldname, value)
			changed = True

	if changed:
		settings.save(ignore_permissions=True)


def _backfill_bag_configuration_links():
	general_configs = {}
	for row in frappe.get_all(
		"Bag Configuration",
		filters={"rate_type": "General"},
		fields=["name", "weight_kg", "uom", "commodity"],
	):
		key = _config_match_key(row.uom, row.weight_kg, row.commodity)
		general_configs[key] = row.name

	_backfill_child_table("Bag Details", "Inward Aawak", general_configs)
	_backfill_child_table("Jawak Bag Detail", "Outward Jawak", general_configs)


def _backfill_child_table(child_doctype, parenttype, general_configs):
	if not frappe.db.has_column(child_doctype, "bag_configuration"):
		return

	fields = ["name", "uom", "commodity", "weight_kg"]
	if frappe.db.has_column(child_doctype, "bag_weight"):
		fields.append("bag_weight")
	if child_doctype == "Jawak Bag Detail" and frappe.db.has_column(child_doctype, "bag_type"):
		fields.append("bag_type")

	rows = frappe.get_all(
		child_doctype,
		filters={"parenttype": parenttype, "bag_configuration": ("is", "not set")},
		fields=fields,
	)

	for row in rows:
		weight = row.weight_kg or row.bag_weight
		if child_doctype == "Jawak Bag Detail" and not weight:
			weight = row.get("bag_type")
		uom = row.uom or "Bag"
		config_name = general_configs.get(_config_match_key(uom, weight, row.commodity))
		if config_name:
			frappe.db.set_value(child_doctype, row.name, "bag_configuration", config_name, update_modified=False)
		elif child_doctype == "Jawak Bag Detail" and row.get("bag_type"):
			config_name = general_configs.get(_config_match_key("Bag", row.bag_type, None))
			if config_name:
				frappe.db.set_value(
					child_doctype, row.name, "bag_configuration", config_name, update_modified=False
				)


def _config_match_key(uom, weight_kg, commodity):
	weight_part = ""
	if weight_kg not in (None, "", 0):
		try:
			weight_part = str(int(float(weight_kg)))
		except (TypeError, ValueError):
			weight_part = str(weight_kg).strip()

	return f"{commodity or ''}|{(uom or 'Bag').strip()}|{weight_part}"
