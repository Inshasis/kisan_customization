# Copyright (c) 2026, Hidayatali and contributors

import frappe

TIERED_FLAGS = {
	"Moise": 1,
	"Damage": 0,
	"S/S": 0,
}


def execute():
	for name, tiered in TIERED_FLAGS.items():
		if frappe.db.exists("Deduction Type", name):
			frappe.db.set_value(
				"Deduction Type", name, "tiered_calculation", tiered, update_modified=False
			)

	frappe.db.commit()
