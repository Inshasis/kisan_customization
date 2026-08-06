# Copyright (c) 2026, Hidayatali and contributors

import json

import frappe
from frappe.utils import flt

from kisan_customization.utils.account_utils import get_all_deduction_accounts


def _remove_deduction_taxes(doc, deduction_accounts):
	for tax in list(doc.get("taxes") or []):
		if tax.account_head in deduction_accounts:
			doc.remove(tax)


def _apply_deduction_rows(doc, deductions):
	deduction_accounts = set(get_all_deduction_accounts(doc.company) or [])
	_remove_deduction_taxes(doc, deduction_accounts)

	cost_center = doc.cost_center or frappe.get_cached_value(
		"Company", doc.company, "cost_center"
	)

	for row in deductions:
		amount = flt(row.get("amount"))
		if not amount:
			continue

		dt = frappe.get_cached_value(
			"Deduction Type",
			row.get("deduction_type"),
			["deduction_type_name", "related_account"],
			as_dict=True,
		)
		if not dt or not dt.related_account:
			frappe.throw(
				frappe._("Related Account not found for Deduction Type {0}").format(
					row.get("deduction_type")
				)
			)

		doc.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Deduct",
				"charge_type": "Actual",
				"account_head": dt.related_account,
				"description": dt.deduction_type_name,
				"rate": 0,
				"tax_amount": amount,
				"cost_center": cost_center,
			},
		)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


@frappe.whitelist()
def get_deduction_data(purchase_invoice):
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)

	deduction_types = frappe.get_all(
		"Deduction Type",
		filters={"is_active": 1, "company": pi.company},
		fields=["name", "deduction_type_name", "related_account"],
		order_by="deduction_type_name asc",
	)

	existing_amounts = {}
	for tax in pi.get("taxes") or []:
		if not tax.account_head:
			continue
		dt_name = frappe.db.get_value(
			"Deduction Type",
			{"related_account": tax.account_head, "company": pi.company},
			"name",
		)
		if dt_name:
			existing_amounts[dt_name] = flt(tax.tax_amount)

	return [
		{
			"deduction_type": dt.name,
			"deduction_type_name": dt.deduction_type_name,
			"related_account": dt.related_account,
			"amount": existing_amounts.get(dt.name, 0),
		}
		for dt in deduction_types
	]


@frappe.whitelist()
def apply_deductions(purchase_invoice, deductions):
	if isinstance(deductions, str):
		deductions = json.loads(deductions)

	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	_apply_deduction_rows(pi, deductions)
	pi.save()

	return {"message": "Deductions applied successfully"}
