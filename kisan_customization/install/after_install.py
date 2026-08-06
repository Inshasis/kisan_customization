# Copyright (c) 2026, Hidayatali and contributors

import frappe

DEFAULT_DEDUCTION_TYPES = [
	"Moise",
	"Damage",
	"S/S",
	"PP",
	"UNLOADING",
	"Others",
	"Weighbridge",
	"RTGS",
	"Miscellaneous",
]

DEFAULT_BAG_DEDUCTIONS = [
	{"bag_type": "PP Bag", "charges": 10.0},
	{"bag_type": "Jute Bag", "charges": 0.6},
]


def after_install():
	setup_master_settings()
	setup_default_deduction_types()


def setup_master_settings():
	if frappe.db.exists("Kisan Master Settings", "Kisan Master Settings"):
		settings = frappe.get_single("Kisan Master Settings")
	else:
		settings = frappe.new_doc("Kisan Master Settings")

	if not settings.default_company:
		settings.default_company = frappe.defaults.get_global_default("company")

	if not settings.bag_wise_deductions:
		for row in DEFAULT_BAG_DEDUCTIONS:
			settings.append("bag_wise_deductions", row)

	settings.save(ignore_permissions=True)


def setup_default_deduction_types():
	company = frappe.get_single("Kisan Master Settings").default_company
	if not company:
		company = frappe.defaults.get_global_default("company")
	if not company:
		return

	for name in DEFAULT_DEDUCTION_TYPES:
		if frappe.db.exists("Deduction Type", name):
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Deduction Type",
				"deduction_type_name": name,
				"company": company,
				"is_active": 1,
			}
		)
		doc.insert(ignore_permissions=True)
