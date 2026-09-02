# Copyright (c) 2026, Hidayatali and contributors

import frappe

DEFAULT_BAG_DEDUCTIONS = [
	{"bag_type": "plastic", "charges": 0.2},
	{"bag_type": "jute", "charges": 0.6},
]

DEFAULT_TIER_RANGES = [
	{"range_from": 10.0, "range_to": 18.0, "multiplier": 1.0},
	{"range_from": 19.0, "range_to": 22.0, "multiplier": 2.0},
	{"range_from": 23.0, "range_to": 999.0, "multiplier": 3.0},
]


def after_install():
	setup_master_settings()
	setup_default_deduction_types()


def setup_master_settings():
	settings = frappe.get_single("Kisan Master Settings")

	if settings.meta.has_field("default_company") and not settings.default_company:
		settings.default_company = frappe.defaults.get_global_default("company")

	if settings.meta.has_field("bag_wise_deductions") and not settings.bag_wise_deductions:
		for row in DEFAULT_BAG_DEDUCTIONS:
			settings.append("bag_wise_deductions", row)

	if settings.meta.has_field("deduction_tier_range") and not settings.deduction_tier_range:
		for row in DEFAULT_TIER_RANGES:
			settings.append("deduction_tier_range", row)

	_set_default_if_empty(settings, "debit_note_cgst_rate", 2.5)
	_set_default_if_empty(settings, "debit_note_sgst_rate", 2.5)
	_set_default_if_empty(settings, "debit_note_igst_rate", 5.0)
	_set_default_if_empty(settings, "days_per_month", 30)
	_set_default_if_empty(settings, "minimum_chargeable_days", 15)
	_set_default_if_empty(settings, "extra_days_after_minimum", 2)

	settings.save(ignore_permissions=True)


def _set_default_if_empty(settings, fieldname, value):
	if not settings.meta.has_field(fieldname):
		return

	if not settings.get(fieldname):
		settings.set(fieldname, value)


def setup_default_deduction_types():
	from kisan_customization.install.deduction_types import sync_deduction_types

	sync_deduction_types()
