# Copyright (c) 2026, Hidayatali and contributors

import frappe

PP_FORMULA = "plastic_gross_weight * charges_per_unit / 100"


def execute():
	if frappe.db.exists("Deduction Type", "PP"):
		frappe.db.set_value(
			"Deduction Type",
			"PP",
			"calculation",
			PP_FORMULA,
			update_modified=False,
		)

	frappe.db.commit()
