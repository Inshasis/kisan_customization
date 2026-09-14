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


def ensure_master_settings_defaults():
	"""Fill missing Kisan Master Settings only; never overwrite user configuration."""
	settings = frappe.get_single("Kisan Master Settings")
	changed = False

	if settings.meta.has_field("default_company") and not settings.default_company:
		settings.default_company = frappe.defaults.get_global_default("company")
		changed = True

	if settings.meta.has_field("bag_wise_deductions"):
		changed = _ensure_child_rows(
			settings,
			"bag_wise_deductions",
			DEFAULT_BAG_DEDUCTIONS,
			"bag_type",
		) or changed

	if settings.meta.has_field("deduction_tier_range"):
		changed = _ensure_child_rows(
			settings,
			"deduction_tier_range",
			DEFAULT_TIER_RANGES,
			"range_from",
		) or changed

	for fieldname, value in (
		("debit_note_cgst_rate", 2.5),
		("debit_note_sgst_rate", 2.5),
		("debit_note_igst_rate", 5.0),
		("days_per_month", 30),
		("minimum_chargeable_days", 15),
		("extra_days_after_minimum", 2),
	):
		if _set_default_if_empty(settings, fieldname, value):
			changed = True

	if changed:
		settings.save(ignore_permissions=True)


def _ensure_child_rows(settings, table_field, default_rows, key_field):
	existing_keys = {
		row.get(key_field)
		for row in settings.get(table_field) or []
		if row.get(key_field) is not None
	}
	added = False
	for row in default_rows:
		if row.get(key_field) not in existing_keys:
			settings.append(table_field, row)
			added = True
	return added


def _set_default_if_empty(settings, fieldname, value):
	if not settings.meta.has_field(fieldname):
		return False

	if settings.get(fieldname):
		return False

	settings.set(fieldname, value)
	return True
