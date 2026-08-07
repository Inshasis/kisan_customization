# Copyright (c) 2026, Hidayatali and contributors

import frappe

DEFAULT_FORMULAS = {
	"UNLOADING": "total_bags * charges_per_unit",
	"Others": "net_amount * charges_per_unit / 100",
}


def execute():
	for name, formula in DEFAULT_FORMULAS.items():
		if not frappe.db.exists("Deduction Type", name):
			continue

		if frappe.db.get_value("Deduction Type", name, "calculation"):
			continue

		frappe.db.set_value("Deduction Type", name, "calculation", formula, update_modified=False)

	frappe.db.commit()
