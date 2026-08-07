# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.install.after_install import (
	DEFAULT_BAG_DEDUCTIONS,
	DEFAULT_DEDUCTION_TYPES,
	DEFAULT_TIER_RANGES,
)


def execute():
	seed_master_settings()
	update_deduction_types()


def seed_master_settings():
	settings = frappe.get_single("Kisan Master Settings")

	if not settings.default_company:
		settings.default_company = frappe.defaults.get_global_default("company")

	_migrate_bag_types(settings)

	if not settings.bag_wise_deductions:
		for row in DEFAULT_BAG_DEDUCTIONS:
			settings.append("bag_wise_deductions", row)

	if not settings.deduction_tier_range:
		for row in DEFAULT_TIER_RANGES:
			settings.append("deduction_tier_range", row)

	settings.save(ignore_permissions=True)


def _migrate_bag_types(settings):
	bag_map = {"PP Bag": "plastic", "Jute Bag": "jute", "plastic": "plastic", "jute": "jute"}
	valid = {"plastic", "jute"}
	migrated = []

	for row in settings.get("bag_wise_deductions") or []:
		bag_type = bag_map.get(row.bag_type)
		if bag_type:
			migrated.append({"bag_type": bag_type, "charges": row.charges})

	if migrated:
		settings.set("bag_wise_deductions", [])
		for row in migrated:
			settings.append("bag_wise_deductions", row)
	elif settings.get("bag_wise_deductions"):
		settings.set("bag_wise_deductions", [])


def update_deduction_types():
	company = frappe.get_single("Kisan Master Settings").default_company
	if not company:
		company = frappe.defaults.get_global_default("company")
	if not company:
		return

	for row in DEFAULT_DEDUCTION_TYPES:
		name = row["deduction_type_name"]
		if not frappe.db.exists("Deduction Type", name):
			continue

		frappe.db.set_value(
			"Deduction Type",
			name,
			{
				"required_value": row["required_value"],
				"charges_per_unit": row["charges_per_unit"],
				"deduction_category": row["deduction_category"],
				"tiered_calculation": row["tiered_calculation"],
				"qty_deducation": row.get("qty_deducation", 0),
			},
			update_modified=False,
		)
