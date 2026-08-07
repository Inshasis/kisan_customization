# Copyright (c) 2026, Hidayatali and contributors

import json

import frappe
from frappe.utils import flt

from kisan_customization.utils.deduction_utils import (
	calculate_deduction_amount,
	get_calculation_formula,
	get_calculation_mode,
	get_pi_net_amount,
	get_pi_total_bags,
	get_pi_total_qty,
)


def _parse_tax_meta(description):
	if not description:
		return {}

	label, _, meta_part = description.partition("|")
	meta = {"label": label.strip()}

	if not meta_part:
		return meta

	for part in meta_part.split("|"):
		if ":" in part:
			key, value = part.split(":", 1)
			meta[key.strip()] = value.strip()

	return meta


def _build_tax_description(deduction_name, actual=None):
	if actual is None:
		return deduction_name
	return f"{deduction_name}|actual:{actual}"


def _get_active_deduction_types(company):
	return frappe.get_all(
		"Deduction Type",
		filters={"is_active": 1, "company": company},
		fields=[
			"name",
			"deduction_type_name",
			"related_account",
			"qty_deducation",
			"tiered_calculation",
			"required_value",
			"charges_per_unit",
			"deduction_category",
			"calculation",
		],
		order_by="deduction_type_name asc",
	)


def _get_deduction_lookup(company):
	types = _get_active_deduction_types(company)
	return {
		"by_name": {dt.name: dt for dt in types},
		"by_label": {dt.deduction_type_name: dt for dt in types},
	}


def _get_pi_context(doc):
	return {
		"net_amount": get_pi_net_amount(doc),
		"total_qty": get_pi_total_qty(doc),
		"total_bags": get_pi_total_bags(doc),
	}


def _is_deduction_tax_row(tax, by_label):
	if tax.add_deduct_tax != "Deduct" or not tax.description:
		return False
	label = _parse_tax_meta(tax.description).get("label")
	return label in by_label


def _remove_deduction_taxes(doc, by_label):
	for tax in list(doc.get("taxes") or []):
		if _is_deduction_tax_row(tax, by_label):
			doc.remove(tax)


def _get_existing_deductions(pi, by_label):
	existing = {}

	for tax in pi.get("taxes") or []:
		if not _is_deduction_tax_row(tax, by_label):
			continue

		label = _parse_tax_meta(tax.description).get("label")
		dt = by_label.get(label)
		if not dt:
			continue

		meta = _parse_tax_meta(tax.description)
		existing[dt.name] = {
			"amount": flt(tax.tax_amount),
			"actual": flt(meta.get("actual")),
		}

	return existing


def _resolve_amount(dt, ctx, actual=0, manual_amount=0, saved_amount=0):
	mode = get_calculation_mode(dt)
	auto_modes = {"formula", "direct"}

	if mode in auto_modes:
		amount, difference, required = calculate_deduction_amount(
			dt,
			actual=actual,
			net_amount=ctx["net_amount"],
			total_qty=ctx["total_qty"],
			total_bags=ctx["total_bags"],
		)
		return amount, difference, required, mode

	if mode == "qty_deducation":
		if actual:
			amount, difference, required = calculate_deduction_amount(
				dt,
				actual=actual,
				net_amount=ctx["net_amount"],
				total_qty=ctx["total_qty"],
				total_bags=ctx["total_bags"],
			)
		else:
			difference = max(0, actual - flt(dt.required_value))
			amount = saved_amount
			required = flt(dt.required_value)
		return amount, difference, required, mode

	amount = flt(manual_amount or saved_amount)
	return amount, 0, flt(dt.required_value), mode


def _apply_deduction_rows(doc, deductions):
	lookup = _get_deduction_lookup(doc.company)
	_remove_deduction_taxes(doc, lookup["by_label"])

	ctx = _get_pi_context(doc)
	cost_center = doc.cost_center or frappe.get_cached_value(
		"Company", doc.company, "cost_center"
	)

	for row in deductions:
		dt = lookup["by_name"].get(row.get("deduction_type"))
		if not dt:
			continue

		actual = flt(row.get("actual"))
		manual_amount = flt(row.get("amount"))
		amount, _, _, mode = _resolve_amount(
			dt, ctx, actual=actual, manual_amount=manual_amount
		)

		if not amount:
			continue

		if not dt.related_account:
			frappe.throw(
				frappe._("Related Account not set for Deduction Type {0}").format(
					dt.deduction_type_name
				)
			)

		description = _build_tax_description(
			dt.deduction_type_name,
			actual if mode == "qty_deducation" else None,
		)

		doc.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Deduct",
				"charge_type": "Actual",
				"account_head": dt.related_account,
				"description": description,
				"rate": 0,
				"tax_amount": amount,
				"cost_center": cost_center,
			},
		)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def _build_deduction_row(dt, ctx, saved=None):
	saved = saved or {}
	actual = saved.get("actual", 0)
	saved_amount = saved.get("amount", 0)

	amount, difference, required, mode = _resolve_amount(
		dt, ctx, actual=actual, saved_amount=saved_amount
	)

	return {
		"deduction_type": dt.name,
		"deduction_type_name": dt.deduction_type_name,
		"related_account": dt.related_account,
		"qty_deducation": dt.qty_deducation,
		"tiered_calculation": dt.tiered_calculation,
		"required_value": dt.required_value,
		"charges_per_unit": dt.charges_per_unit,
		"deduction_category": dt.deduction_category,
		"calculation": dt.calculation,
		"calculation_mode": mode,
		"formula": get_calculation_formula(
			dt,
			ctx["total_bags"],
			ctx["net_amount"],
			ctx["total_qty"],
			actual,
			difference,
		),
		"net_amount": ctx["net_amount"],
		"total_qty": ctx["total_qty"],
		"total_bags": ctx["total_bags"],
		"actual": actual,
		"difference": difference,
		"amount": amount,
	}


@frappe.whitelist()
def get_deduction_data(purchase_invoice):
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	ctx = _get_pi_context(pi)
	lookup = _get_deduction_lookup(pi.company)
	existing = _get_existing_deductions(pi, lookup["by_label"])

	result = [
		_build_deduction_row(dt, ctx, existing.get(dt.name))
		for dt in lookup["by_name"].values()
	]

	return sorted(result, key=lambda row: row["deduction_type_name"])


@frappe.whitelist()
def calculate_deduction_preview(purchase_invoice, deduction_type, actual):
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	ctx = _get_pi_context(pi)
	dt = frappe.get_cached_value(
		"Deduction Type",
		deduction_type,
		[
			"deduction_type_name",
			"qty_deducation",
			"tiered_calculation",
			"deduction_category",
			"required_value",
			"charges_per_unit",
			"calculation",
		],
		as_dict=True,
	)

	amount, difference, required, mode = _resolve_amount(
		dt, ctx, actual=flt(actual)
	)

	return {
		"actual": flt(actual),
		"required_value": required,
		"difference": difference,
		"amount": amount,
		"net_amount": ctx["net_amount"],
		"total_bags": ctx["total_bags"],
		"calculation_mode": mode,
		"formula": get_calculation_formula(
			dt, ctx["total_bags"], ctx["net_amount"], ctx["total_qty"], flt(actual)
		),
	}


@frappe.whitelist()
def apply_deductions(purchase_invoice, deductions):
	if isinstance(deductions, str):
		deductions = json.loads(deductions)

	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	_apply_deduction_rows(pi, deductions)
	pi.save()

	return {"message": "Deductions applied successfully"}
