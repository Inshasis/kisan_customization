# Copyright (c) 2026, Hidayatali and contributors

import frappe

AUTO_DEDUCTION_TYPES = [
	{
		"deduction_type_name": "Bag Deduction",
		"is_active": 1,
		"qty_deducation": 0,
		"tiered_calculation": 0,
		"deduction_category": "single",
	},
	{
		"deduction_type_name": "Weight Deduction",
		"is_active": 1,
		"qty_deducation": 0,
		"tiered_calculation": 0,
		"deduction_category": "single",
	},
]


def execute():
	companies = frappe.get_all("Company", pluck="name")
	if not companies:
		return

	for company in companies:
		for row in AUTO_DEDUCTION_TYPES:
			_ensure_deduction_type(company, row)


def _ensure_deduction_type(company, row):
	name = row["deduction_type_name"]
	existing = frappe.db.get_value(
		"Deduction Type",
		{"deduction_type_name": name, "company": company},
		"name",
	)
	if existing:
		frappe.db.set_value(
			"Deduction Type",
			existing,
			{
				"is_active": 1,
				"qty_deducation": 0,
				"tiered_calculation": 0,
				"deduction_category": "single",
			},
			update_modified=False,
		)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Deduction Type",
			"company": company,
			**row,
		}
	)
	doc.insert(ignore_permissions=True)
