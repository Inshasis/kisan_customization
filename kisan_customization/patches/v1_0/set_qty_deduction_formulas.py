# Copyright (c) 2026, Hidayatali and contributors

import frappe

QTY_DEDUCTION_FORMULAS = {
	"Moise": "difference * total_amount / 100",
	"Damage": "difference * charges_per_unit * total_gross_weight / 100",
	"S/S": "difference * total_amount / 100",
}

TIERED_FLAGS = {
	"Moise": 1,
	"Damage": 0,
	"S/S": 0,
}


def execute():
	for name, formula in QTY_DEDUCTION_FORMULAS.items():
		if not frappe.db.exists("Deduction Type", name):
			continue

		if not frappe.db.get_value("Deduction Type", name, "qty_deducation"):
			continue

		frappe.db.set_value("Deduction Type", name, "calculation", formula, update_modified=False)

		if name in TIERED_FLAGS:
			frappe.db.set_value(
				"Deduction Type",
				name,
				"tiered_calculation",
				TIERED_FLAGS[name],
				update_modified=False,
			)

	frappe.db.commit()
