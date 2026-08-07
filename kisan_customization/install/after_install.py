# Copyright (c) 2026, Hidayatali and contributors

import frappe

DEFAULT_DEDUCTION_TYPES = [
	{
		"deduction_type_name": "Moise",
		"required_value": 10.0,
		"charges_per_unit": 0.0,
		"calculation": "difference * total_amount / 100",
		"deduction_category": "multiple",
		"tiered_calculation": 1,
		"qty_deducation": 1,
		"is_active": 1,
	},
	{
		"deduction_type_name": "Damage",
		"required_value": 2.0,
		"charges_per_unit": 15.0,
		"calculation": "difference * charges_per_unit * total_gross_weight / 100",
		"deduction_category": "multiple",
		"tiered_calculation": 0,
		"qty_deducation": 1,
		"is_active": 1,
	},
	{
		"deduction_type_name": "S/S",
		"required_value": 2.0,
		"charges_per_unit": 0.0,
		"calculation": "difference * total_amount / 100",
		"deduction_category": "multiple",
		"tiered_calculation": 0,
		"qty_deducation": 1,
		"is_active": 1,
	},
	{
		"deduction_type_name": "PP",
		"required_value": 0.0,
		"charges_per_unit": 10.0,
		"calculation": "plastic_gross_weight * charges_per_unit / 100",
		"deduction_category": "single",
		"tiered_calculation": 0,
		"qty_deducation": 0,
		"is_active": 1,
	},
	{
		"deduction_type_name": "UNLOADING",
		"required_value": 0.0,
		"charges_per_unit": 12.0,
		"calculation": "total_bags * charges_per_unit",
		"deduction_category": "single",
		"tiered_calculation": 0,
		"qty_deducation": 0,
		"is_active": 1,
	},
	{
		"deduction_type_name": "Others",
		"required_value": 0.0,
		"charges_per_unit": 1.5,
		"calculation": "net_amount * charges_per_unit / 100",
		"deduction_category": "single",
		"tiered_calculation": 0,
		"qty_deducation": 0,
		"is_active": 1,
	},
	{
		"deduction_type_name": "Weighbridge",
		"required_value": 0.0,
		"charges_per_unit": 100.0,
		"deduction_category": "single",
		"tiered_calculation": 0,
		"qty_deducation": 0,
		"is_active": 1,
	},
	{
		"deduction_type_name": "RTGS",
		"required_value": 0.0,
		"charges_per_unit": 60.0,
		"deduction_category": "single",
		"tiered_calculation": 0,
		"qty_deducation": 0,
		"is_active": 1,
	},
	{
		"deduction_type_name": "Miscellaneous",
		"required_value": 0.0,
		"charges_per_unit": 0.0,
		"deduction_category": "single",
		"tiered_calculation": 0,
		"qty_deducation": 0,
		"is_active": 1,
	},
]

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

	if not settings.default_company:
		settings.default_company = frappe.defaults.get_global_default("company")

	if not settings.bag_wise_deductions:
		for row in DEFAULT_BAG_DEDUCTIONS:
			settings.append("bag_wise_deductions", row)

	if not settings.deduction_tier_range:
		for row in DEFAULT_TIER_RANGES:
			settings.append("deduction_tier_range", row)

	if not settings.debit_note_cgst_rate:
		settings.debit_note_cgst_rate = 2.5
	if not settings.debit_note_sgst_rate:
		settings.debit_note_sgst_rate = 2.5
	if not settings.debit_note_igst_rate:
		settings.debit_note_igst_rate = 5.0
	if not settings.days_per_month:
		settings.days_per_month = 30
	if not settings.minimum_chargeable_days:
		settings.minimum_chargeable_days = 15
	if not settings.extra_days_after_minimum:
		settings.extra_days_after_minimum = 2

	settings.save(ignore_permissions=True)


def setup_default_deduction_types():
	company = frappe.get_single("Kisan Master Settings").default_company
	if not company:
		company = frappe.defaults.get_global_default("company")
	if not company:
		return

	for row in DEFAULT_DEDUCTION_TYPES:
		name = row["deduction_type_name"]
		if frappe.db.exists("Deduction Type", name):
			doc = frappe.get_doc("Deduction Type", name)
			for field, value in row.items():
				if field != "deduction_type_name":
					setattr(doc, field, value)
			doc.company = company
			doc.save(ignore_permissions=True)
			continue

		doc = frappe.get_doc({"doctype": "Deduction Type", "company": company, **row})
		doc.insert(ignore_permissions=True)
