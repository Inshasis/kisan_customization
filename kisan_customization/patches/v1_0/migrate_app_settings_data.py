# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.install.master_settings import (
	DEFAULT_BAG_DEDUCTIONS,
	DEFAULT_TIER_RANGES,
)


def execute():
	seed_master_settings()


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
