# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.purchase_invoice.deductions import (
	_get_deduction_lookup,
	_get_deductions_from_taxes,
	_set_child_table_from_deductions,
)


def execute():
	if not frappe.get_meta("Purchase Invoice").has_field("custom_deductions"):
		return

	invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"docstatus": 0},
		pluck="name",
	)

	for name in invoices:
		pi = frappe.get_doc("Purchase Invoice", name)
		if pi.get("custom_deductions"):
			continue

		lookup = _get_deduction_lookup(pi.company)
		deductions = _get_deductions_from_taxes(pi, lookup)
		if not deductions:
			continue

		_set_child_table_from_deductions(pi, deductions)
		pi.flags.ignore_deduction_recalc = True
		pi.flags.ignore_validate = True
		pi.flags.ignore_mandatory = True
		pi.save(ignore_permissions=True)

	frappe.db.commit()
