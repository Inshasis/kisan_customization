# Copyright (c) 2026, Hidayatali and contributors

import frappe

DEDUCTION_FORMULAS = {
	"Moise": {
		"calculation": "difference * total_arrival_weight * item_rate / 100",
		"deduction_category": "multiple",
	},
	"S/S": {
		"calculation": "difference * total_arrival_weight * item_rate / 100",
		"deduction_category": "multiple",
	},
}


def execute():
	for name, values in DEDUCTION_FORMULAS.items():
		if not frappe.db.exists("Deduction Type", name):
			continue

		frappe.db.set_value(
			"Deduction Type",
			name,
			values,
			update_modified=False,
		)

	frappe.clear_cache(doctype="Deduction Type")
