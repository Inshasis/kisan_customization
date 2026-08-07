# Copyright (c) 2026, Hidayatali and contributors

import json

import frappe
from frappe.utils import flt

from kisan_customization.purchase_invoice.bags import (
	get_bag_rows,
	has_plastic_bag,
)
from kisan_customization.utils.deduction_utils import (
	calculate_deduction_amount,
	get_calculation_formula,
	get_calculation_mode,
	get_pi_net_amount,
	get_pi_plastic_gross_weight,
	get_pi_total_arrival_weight,
	get_pi_total_bags,
	get_pi_total_gross_weight,
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


def _build_tax_description(deduction_name, actual=None, bag_type=None):
	parts = [deduction_name]
	if bag_type:
		parts.append(f"bag:{bag_type}")
	if actual is not None:
		parts.append(f"actual:{actual}")
	return "|".join(parts)


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
	net_amount = get_pi_net_amount(doc)

	return {
		"net_amount": net_amount,
		"total_amount": net_amount,
		"total_qty": get_pi_total_qty(doc),
		"total_bags": get_pi_total_bags(doc),
		"total_gross_weight": get_pi_total_gross_weight(doc),
		"total_arrival_weight": get_pi_total_arrival_weight(doc),
		"plastic_gross_weight": get_pi_plastic_gross_weight(doc),
	}


def _bag_context(base_ctx, bag):
	return {
		**base_ctx,
		"total_bags": bag["no_of_bags"],
		"total_gross_weight": bag["gross_weight_kg"],
		"total_arrival_weight": bag["arrival_qty_kg"],
	}


def _calc_kwargs(ctx, actual=0):
	return {
		"actual": actual,
		"net_amount": ctx["net_amount"],
		"total_qty": ctx["total_qty"],
		"total_bags": ctx["total_bags"],
		"total_gross_weight": ctx["total_gross_weight"],
		"total_arrival_weight": ctx["total_arrival_weight"],
		"plastic_gross_weight": ctx["plastic_gross_weight"],
	}


def _deduction_tax_label(tax, by_label):
	if tax.add_deduct_tax != "Deduct" or not tax.description:
		return None

	meta = _parse_tax_meta(tax.description)
	label = meta.get("label")
	if label not in by_label:
		return None

	bag_type = meta.get("bag") or ""
	return f"{label}|{bag_type}"


def _is_deduction_tax_row(tax, by_label):
	return _deduction_tax_label(tax, by_label) is not None


def _remove_deduction_taxes(doc, by_label):
	for tax in list(doc.get("taxes") or []):
		if _is_deduction_tax_row(tax, by_label):
			doc.remove(tax)


def _get_existing_deductions(pi, by_label):
	existing = {}

	for tax in pi.get("taxes") or []:
		key = _deduction_tax_label(tax, by_label)
		if not key:
			continue

		label, _, bag_type = key.partition("|")
		dt = by_label.get(label)
		if not dt:
			continue

		meta = _parse_tax_meta(tax.description)
		existing_key = (dt.name, bag_type)
		existing[existing_key] = {
			"amount": flt(tax.tax_amount),
			"actual": flt(meta.get("actual")),
		}

	return existing


def _should_skip_deduction(dt, doc):
	name = (dt.deduction_type_name or "").upper()
	if name == "PP" and not has_plastic_bag(doc):
		return True
	return False


def _resolve_amount(dt, ctx, actual=0, manual_amount=0, saved_amount=0):
	mode = get_calculation_mode(dt)
	auto_modes = {"formula", "direct"}

	if mode in auto_modes:
		amount, difference, required = calculate_deduction_amount(dt, **_calc_kwargs(ctx, actual))
		return amount, difference, required, mode

	if mode == "qty_deducation":
		if actual:
			amount, difference, required = calculate_deduction_amount(dt, **_calc_kwargs(ctx, actual))
		else:
			difference = max(0, actual - flt(dt.required_value))
			amount = saved_amount
			required = flt(dt.required_value)
		return amount, difference, required, mode

	amount = flt(manual_amount or saved_amount)
	return amount, 0, flt(dt.required_value), mode


def _display_name(dt, bag_type=None):
	if bag_type:
		return f"{dt.deduction_type_name} ({bag_type})"
	return dt.deduction_type_name


def _build_deduction_row(dt, ctx, saved=None, bag=None):
	saved = saved or {}
	actual = saved.get("actual", 0)
	saved_amount = saved.get("amount", 0)
	row_ctx = _bag_context(ctx, bag) if bag else ctx

	amount, difference, required, mode = _resolve_amount(
		dt, row_ctx, actual=actual, saved_amount=saved_amount
	)

	bag_type = bag["bag_type"] if bag else None

	return {
		"deduction_type": dt.name,
		"deduction_type_name": _display_name(dt, bag_type),
		"bag_type": bag_type or "",
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
			total_bags=row_ctx["total_bags"],
			net_amount=row_ctx["net_amount"],
			total_qty=row_ctx["total_qty"],
			total_gross_weight=row_ctx["total_gross_weight"],
			total_arrival_weight=row_ctx["total_arrival_weight"],
			plastic_gross_weight=row_ctx["plastic_gross_weight"],
			actual=actual,
			difference=difference,
		),
		"net_amount": row_ctx["net_amount"],
		"total_qty": row_ctx["total_qty"],
		"total_bags": row_ctx["total_bags"],
		"total_gross_weight": row_ctx["total_gross_weight"],
		"actual": actual,
		"difference": difference,
		"amount": amount,
	}


def _get_deductions_from_taxes(doc, lookup):
	deductions = []

	for tax in doc.get("taxes") or []:
		key = _deduction_tax_label(tax, lookup["by_label"])
		if not key:
			continue

		label, _, bag_type = key.partition("|")
		dt = lookup["by_label"].get(label)
		if not dt:
			continue

		meta = _parse_tax_meta(tax.description)
		deductions.append(
			{
				"deduction_type": dt.name,
				"actual": flt(meta.get("actual")),
				"bag_type": bag_type,
				"amount": flt(tax.tax_amount),
			}
		)

	return deductions


def recalculate_existing_deductions(doc):
	if doc.flags.get("ignore_deduction_recalc"):
		return

	lookup = _get_deduction_lookup(doc.company)
	deductions = _get_deductions_from_taxes(doc, lookup)
	if not deductions:
		return

	_apply_deduction_rows(doc, deductions)


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
		bag_type = row.get("bag_type") or ""

		bag_rows = get_bag_rows(doc)
		bag = next((b for b in bag_rows if b["bag_type"] == bag_type), None) if bag_type else None
		row_ctx = _bag_context(ctx, bag) if bag else ctx

		amount, _, _, mode = _resolve_amount(
			dt, row_ctx, actual=actual, manual_amount=manual_amount
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
			bag_type=bag_type or None,
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


@frappe.whitelist()
def get_deduction_data(purchase_invoice):
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	ctx = _get_pi_context(pi)
	lookup = _get_deduction_lookup(pi.company)
	existing = _get_existing_deductions(pi, lookup["by_label"])
	bag_rows = get_bag_rows(pi)

	result = []

	for dt in lookup["by_name"].values():
		if _should_skip_deduction(dt, pi):
			continue

		if dt.qty_deducation and dt.deduction_category == "multiple" and bag_rows:
			for bag in bag_rows:
				saved = existing.get((dt.name, bag["bag_type"]), {})
				result.append(_build_deduction_row(dt, ctx, saved, bag))
		else:
			saved = existing.get((dt.name, ""), {})
			result.append(_build_deduction_row(dt, ctx, saved))

	return sorted(result, key=lambda row: row["deduction_type_name"])


@frappe.whitelist()
def calculate_deduction_preview(purchase_invoice, deduction_type, actual, bag_type=None):
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

	bag = None
	if bag_type:
		bag = next((b for b in get_bag_rows(pi) if b["bag_type"] == bag_type), None)

	row_ctx = _bag_context(ctx, bag) if bag else ctx
	amount, difference, required, mode = _resolve_amount(dt, row_ctx, actual=flt(actual))

	return {
		"actual": flt(actual),
		"required_value": required,
		"difference": difference,
		"amount": amount,
		"net_amount": row_ctx["net_amount"],
		"total_bags": row_ctx["total_bags"],
		"total_gross_weight": row_ctx["total_gross_weight"],
		"calculation_mode": mode,
		"formula": get_calculation_formula(
			dt,
			total_bags=row_ctx["total_bags"],
			net_amount=row_ctx["net_amount"],
			total_qty=row_ctx["total_qty"],
			total_gross_weight=row_ctx["total_gross_weight"],
			total_arrival_weight=row_ctx["total_arrival_weight"],
			plastic_gross_weight=row_ctx["plastic_gross_weight"],
			actual=flt(actual),
			difference=difference,
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
