# Copyright (c) 2026, Hidayatali and contributors

import json
import re

import frappe
from frappe import _
from frappe.utils import flt

from kisan_customization.purchase_invoice.bags import (
	calculate_bag_deduction,
	calculate_weight_deduction,
	get_bag_rows,
	get_pi_item_rate,
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

CHILD_TABLE_FIELD = "custom_deductions"
BAG_DEDUCTION_NAME = "Bag Deduction"
WEIGHT_DEDUCTION_NAME = "Weight Deduction"
AUTO_DEDUCTION_NAMES = {BAG_DEDUCTION_NAME, WEIGHT_DEDUCTION_NAME}
BAG_WISE_ARRIVAL_DEDUCTION_TYPES = frozenset({"Moise", "S/S"})
DEDUCTION_ITEM_CODE = "Quality & Other"


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


def _build_tax_description(deduction_name, actual=None, bag_type=None, no_of_bags=0):
	parts = [deduction_name]
	if bag_type:
		parts.append(f"bag:{bag_type}")
	if no_of_bags:
		parts.append(f"bags:{int(flt(no_of_bags))}")
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
		"item_rate": get_pi_item_rate(doc),
	}


def _get_pi_item_rate(doc):
	return get_pi_item_rate(doc)


def _calculate_bag_deduction_amount(doc):
	return calculate_bag_deduction(doc)


def _calculate_weight_deduction_amount(doc):
	return calculate_weight_deduction(doc)


def _build_auto_deduction_dialog_row(doc, name, calculation_mode, is_bag_deduction=0, is_weight_deduction=0):
	if is_bag_deduction:
		deduction_kg, item_rate, amount = _calculate_bag_deduction_amount(doc)
		gross_weight = get_pi_total_gross_weight(doc)
		arrival_weight = get_pi_total_arrival_weight(doc)
		formula = f"{gross_weight} - {arrival_weight} = {deduction_kg} kg × Avg. Rate {item_rate} / 100"
	elif is_weight_deduction:
		deduction_kg, item_rate, amount = _calculate_weight_deduction_amount(doc)
		accepted_qty_kg = flt(get_pi_total_qty(doc)) * 100
		gross_weight = get_pi_total_gross_weight(doc)
		formula = f"{accepted_qty_kg} - {gross_weight} = {deduction_kg} kg × {item_rate} / 100"
	else:
		return None

	if not deduction_kg and not amount:
		return None

	deduction_dt = _get_auto_deduction_type(doc.company, name)
	ctx = _get_pi_context(doc)

	return {
		"deduction_type": deduction_dt.name if deduction_dt else "",
		"deduction_type_name": name,
		"bag_type": "",
		"related_account": deduction_dt.related_account if deduction_dt else "",
		"is_bag_deduction": is_bag_deduction,
		"is_weight_deduction": is_weight_deduction,
		"weight_deduction_kg": deduction_kg,
		"item_rate": item_rate,
		"qty_deducation": 0,
		"calculation_mode": calculation_mode,
		"formula": formula,
		"net_amount": ctx["net_amount"],
		"total_bags": ctx["total_bags"],
		"total_gross_weight": ctx["total_gross_weight"],
		"actual": 0,
		"difference": 0,
		"amount": amount,
	}


def _build_bag_deduction_dialog_row(doc):
	return _build_auto_deduction_dialog_row(
		doc,
		BAG_DEDUCTION_NAME,
		"bag_deduction",
		is_bag_deduction=1,
	)


def _build_weight_deduction_dialog_row(doc):
	return _build_auto_deduction_dialog_row(
		doc,
		WEIGHT_DEDUCTION_NAME,
		"weight_deduction",
		is_weight_deduction=1,
	)


def _parse_no_of_bags_from_name(deduction_type_name):
	if not deduction_type_name:
		return 0

	match = re.search(r"×\s*(\d+)", deduction_type_name)
	if match:
		return flt(match.group(1))
	return 0


def _deduction_row_key(deduction_type, bag_type="", no_of_bags=0):
	return (deduction_type, bag_type or "", int(flt(no_of_bags)))


def _find_bag_row(bag_rows, bag_type, no_of_bags=0, gross_weight_kg=0):
	if not bag_type:
		return None

	candidates = [bag for bag in bag_rows if bag.get("bag_type") == bag_type]
	if not candidates:
		return None

	no_of_bags = flt(no_of_bags)
	if no_of_bags:
		matched = [bag for bag in candidates if flt(bag.get("no_of_bags")) == no_of_bags]
		if len(matched) == 1:
			return matched[0]

	gross_weight_kg = flt(gross_weight_kg)
	if gross_weight_kg:
		matched = [bag for bag in candidates if flt(bag.get("gross_weight_kg")) == gross_weight_kg]
		if len(matched) == 1:
			return matched[0]

	if len(candidates) == 1:
		return candidates[0]

	return None


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
		"item_rate": ctx.get("item_rate", 0),
	}


def _uses_bag_wise_arrival(dt):
	return (dt.deduction_type_name or "").strip() in BAG_WISE_ARRIVAL_DEDUCTION_TYPES


def _deduction_tax_label(tax, by_label):
	if tax.add_deduct_tax != "Deduct" or not tax.description:
		return None

	meta = _parse_tax_meta(tax.description)
	label = meta.get("label")
	if label not in by_label and label not in AUTO_DEDUCTION_NAMES:
		return None

	bag_type = meta.get("bag") or ""
	return f"{label}|{bag_type}"


def _is_deduction_tax_row(tax, by_label):
	return _deduction_tax_label(tax, by_label) is not None


def _remove_deduction_taxes(doc, by_label=None):
	for tax in list(doc.get("taxes") or []):
		if tax.add_deduct_tax != "Deduct":
			continue

		if tax.description and tax.description.startswith("Deductions:"):
			doc.remove(tax)
			continue

		if by_label and _is_deduction_tax_row(tax, by_label):
			doc.remove(tax)


def _get_existing_deductions_from_taxes(pi, by_label):
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
		bags = flt(meta.get("bags"))
		existing_key = _deduction_row_key(dt.name, bag_type, bags)
		existing[existing_key] = {
			"amount": flt(tax.tax_amount),
			"actual": flt(meta.get("actual")),
		}

	return existing


def _get_existing_deductions_from_child(doc):
	existing = {}

	for row in doc.get(CHILD_TABLE_FIELD) or []:
		if row.get("is_weight_deduction") or row.get("is_bag_deduction"):
			continue

		no_of_bags = flt(getattr(row, "no_of_bags", None))
		if not no_of_bags:
			no_of_bags = _parse_no_of_bags_from_name(row.deduction_type_name)

		key = _deduction_row_key(row.deduction_type, row.bag_type, no_of_bags)
		existing[key] = {
			"amount": flt(row.amount),
			"actual": flt(row.actual),
			"related_account": row.related_account,
			"no_of_bags": no_of_bags,
		}

	return existing


def _get_existing_deductions(doc, lookup):
	existing = _get_existing_deductions_from_child(doc)
	if existing:
		return existing

	return _get_existing_deductions_from_taxes(doc, lookup["by_label"])


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


def _display_name(dt, bag_type=None, no_of_bags=0):
	if bag_type:
		bags = int(flt(no_of_bags))
		if bags:
			return f"{dt.deduction_type_name} ({bag_type} × {bags})"
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
	no_of_bags = flt(bag["no_of_bags"]) if bag else 0

	return {
		"deduction_type": dt.name,
		"deduction_type_name": _display_name(dt, bag_type, no_of_bags),
		"bag_type": bag_type or "",
		"no_of_bags": flt(bag["no_of_bags"]) if bag else 0,
		"related_account": dt.related_account or saved.get("related_account") or "",
		"qty_deducation": dt.qty_deducation,
		"tiered_calculation": dt.tiered_calculation,
		"required_value": required or flt(dt.required_value),
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
			item_rate=row_ctx.get("item_rate", 0),
		),
		"net_amount": row_ctx["net_amount"],
		"total_qty": row_ctx["total_qty"],
		"total_bags": row_ctx["total_bags"],
		"total_gross_weight": row_ctx["total_gross_weight"],
		"total_arrival_weight": row_ctx["total_arrival_weight"],
		"item_rate": row_ctx.get("item_rate", 0),
		"actual": actual,
		"difference": difference,
		"amount": amount,
	}


def _child_row_dict(
	dt,
	amount,
	actual=0,
	difference=0,
	required=0,
	bag_type="",
	weight_deduction_kg=0,
	item_rate=0,
	is_weight_deduction=0,
	is_bag_deduction=0,
	no_of_bags=0,
):
	if is_bag_deduction:
		display = BAG_DEDUCTION_NAME
	elif is_weight_deduction:
		display = WEIGHT_DEDUCTION_NAME
	else:
		display = _display_name(dt, bag_type or None, no_of_bags)
	return {
		"deduction_type": dt.name if dt else None,
		"deduction_type_name": display,
		"bag_type": bag_type or "",
		"no_of_bags": flt(no_of_bags),
		"related_account": (dt.related_account if dt else None) or None,
		"is_weight_deduction": is_weight_deduction,
		"is_bag_deduction": is_bag_deduction,
		"actual": flt(actual),
		"required_value": flt(required),
		"difference": flt(difference),
		"weight_deduction_kg": flt(weight_deduction_kg),
		"item_rate": flt(item_rate),
		"amount": flt(amount),
	}


def _get_auto_deduction_type(company, deduction_type_name):
	return frappe.db.get_value(
		"Deduction Type",
		{
			"deduction_type_name": deduction_type_name,
			"company": company,
			"is_active": 1,
		},
		["name", "deduction_type_name", "related_account"],
		as_dict=True,
	)


def _get_weight_deduction_type(company):
	return _get_auto_deduction_type(company, WEIGHT_DEDUCTION_NAME)


def _get_bag_deduction_type(company):
	return _get_auto_deduction_type(company, BAG_DEDUCTION_NAME)


def _resolve_related_account(row, lookup, company=None):
	if row.get("is_bag_deduction"):
		bag_dt = lookup["by_label"].get(BAG_DEDUCTION_NAME) or _get_bag_deduction_type(company)
		if bag_dt:
			return bag_dt.related_account
		return row.get("related_account")

	if row.get("is_weight_deduction"):
		weight_dt = lookup["by_label"].get(WEIGHT_DEDUCTION_NAME) or _get_weight_deduction_type(
			company
		)
		if weight_dt:
			return weight_dt.related_account
		return row.get("related_account")

	dt = lookup["by_name"].get(row.deduction_type) if row.get("deduction_type") else None
	if not dt and row.get("deduction_type_name"):
		dt = lookup["by_label"].get(row.deduction_type_name.split(" (")[0])

	if dt and dt.related_account:
		return dt.related_account

	return row.get("related_account")


def sync_auto_deduction_rows(doc):
	bag_deduction, bag_rate, bag_amount = _calculate_bag_deduction_amount(doc)
	weight_deduction, weight_rate, weight_amount = _calculate_weight_deduction_amount(doc)

	if frappe.get_meta("Purchase Invoice").has_field("custom_bag_deduction"):
		doc.custom_bag_deduction = bag_deduction
	if frappe.get_meta("Purchase Invoice").has_field("custom_bag_deduction_amount"):
		doc.custom_bag_deduction_amount = bag_amount
	if frappe.get_meta("Purchase Invoice").has_field("custom_weight_deduction"):
		doc.custom_weight_deduction = weight_deduction
	if frappe.get_meta("Purchase Invoice").has_field("custom_weight_deduction_amount"):
		doc.custom_weight_deduction_amount = weight_amount

	bag_dt = _get_bag_deduction_type(doc.company)
	weight_dt = _get_weight_deduction_type(doc.company)
	rows = list(doc.get(CHILD_TABLE_FIELD) or [])
	manual_rows = [
		row
		for row in rows
		if not row.get("is_weight_deduction") and not row.get("is_bag_deduction")
	]

	doc.set(CHILD_TABLE_FIELD, [])

	for row in manual_rows:
		doc.append(CHILD_TABLE_FIELD, row.as_dict())

	if bag_deduction or bag_amount:
		doc.append(
			CHILD_TABLE_FIELD,
			_child_row_dict(
				bag_dt,
				bag_amount,
				weight_deduction_kg=bag_deduction,
				item_rate=bag_rate,
				is_bag_deduction=1,
			),
		)

	if weight_deduction or weight_amount:
		doc.append(
			CHILD_TABLE_FIELD,
			_child_row_dict(
				weight_dt,
				weight_amount,
				weight_deduction_kg=weight_deduction,
				item_rate=weight_rate,
				is_weight_deduction=1,
			),
		)


def sync_weight_deduction_row(doc):
	sync_auto_deduction_rows(doc)


def _resolve_child_row_amount(doc, row_data, lookup, ctx):
	dt = lookup["by_name"].get(row_data.get("deduction_type"))
	if not dt:
		return None

	actual = flt(row_data.get("actual"))
	manual_amount = flt(row_data.get("amount"))
	bag_type = row_data.get("bag_type") or ""
	no_of_bags = flt(row_data.get("no_of_bags"))

	bag_rows = get_bag_rows(doc)
	bag = _find_bag_row(
		bag_rows,
		bag_type,
		no_of_bags=no_of_bags,
		gross_weight_kg=row_data.get("gross_weight_kg"),
	)
	row_ctx = _bag_context(ctx, bag) if bag else ctx

	amount, difference, required, _mode = _resolve_amount(
		dt, row_ctx, actual=actual, manual_amount=manual_amount
	)

	no_of_bags = flt(bag["no_of_bags"]) if bag else flt(row_data.get("no_of_bags"))

	return _child_row_dict(
		dt,
		amount,
		actual=actual,
		difference=difference,
		required=required,
		bag_type=bag_type,
		no_of_bags=no_of_bags,
	)


def _set_child_table_from_deductions(doc, deductions):
	if not frappe.get_meta("Purchase Invoice").has_field(CHILD_TABLE_FIELD):
		_apply_deduction_rows_legacy(doc, deductions)
		return

	lookup = _get_deduction_lookup(doc.company)
	ctx = _get_pi_context(doc)
	rows = []

	for row in deductions:
		child_row = _resolve_child_row_amount(doc, row, lookup, ctx)
		if child_row and (child_row["amount"] or flt(row.get("actual"))):
			rows.append(child_row)

	doc.set(CHILD_TABLE_FIELD, [])
	for row in rows:
		doc.append(CHILD_TABLE_FIELD, row)

	sync_weight_deduction_row(doc)


def _recalculate_child_table_amounts(doc):
	if not doc.get(CHILD_TABLE_FIELD):
		return

	lookup = _get_deduction_lookup(doc.company)
	ctx = _get_pi_context(doc)
	updated_rows = []

	for row in doc.get(CHILD_TABLE_FIELD) or []:
		if row.get("is_weight_deduction") or row.get("is_bag_deduction"):
			continue

		child_row = _resolve_child_row_amount(
			doc,
			{
				"deduction_type": row.deduction_type,
				"actual": row.actual,
				"bag_type": row.bag_type,
				"no_of_bags": flt(getattr(row, "no_of_bags", None))
				or _parse_no_of_bags_from_name(row.deduction_type_name),
				"amount": row.amount,
			},
			lookup,
			ctx,
		)
		if child_row:
			updated_rows.append(child_row)

	doc.set(CHILD_TABLE_FIELD, updated_rows)
	sync_weight_deduction_row(doc)


def _sync_taxes_from_child_table(doc):
	if not frappe.get_meta("Purchase Invoice").has_field(CHILD_TABLE_FIELD):
		return

	lookup = _get_deduction_lookup(doc.company)
	_remove_deduction_taxes(doc, lookup["by_label"])

	account_groups = {}
	cost_center = doc.cost_center or frappe.get_cached_value(
		"Company", doc.company, "cost_center"
	)

	for row in doc.get(CHILD_TABLE_FIELD) or []:
		amount = flt(row.amount)
		if not amount:
			continue

		account = _resolve_related_account(row, lookup, doc.company)
		if not account:
			continue

		row.related_account = account

		label = row.deduction_type_name or row.deduction_type
		account_groups.setdefault(account, {"total": 0, "labels": []})
		account_groups[account]["total"] += amount
		if label and label not in account_groups[account]["labels"]:
			account_groups[account]["labels"].append(label)

	for account, data in account_groups.items():
		description = "Deductions: " + ", ".join(data["labels"])
		doc.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Deduct",
				"charge_type": "Actual",
				"account_head": account,
				"description": description,
				"rate": 0,
				"tax_amount": flt(data["total"], 2),
				"cost_center": cost_center,
			},
		)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def _migrate_taxes_to_child_table(doc):
	if not frappe.get_meta("Purchase Invoice").has_field(CHILD_TABLE_FIELD):
		return False

	if doc.get(CHILD_TABLE_FIELD):
		return False

	lookup = _get_deduction_lookup(doc.company)
	deductions = _get_deductions_from_taxes(doc, lookup)
	if not deductions:
		return False

	_set_child_table_from_deductions(doc, deductions)
	return True


def _get_deductions_from_taxes(doc, lookup):
	deductions = []

	for tax in doc.get("taxes") or []:
		if tax.description and tax.description.startswith("Deductions:"):
			continue

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
				"no_of_bags": flt(meta.get("bags")),
				"amount": flt(tax.tax_amount),
			}
		)

	return deductions


def recalculate_existing_deductions(doc):
	if doc.flags.get("ignore_deduction_recalc") or doc.get("is_return"):
		return

	if doc.docstatus == 1:
		doc.flags.ignore_validate_update_after_submit = True

	if not frappe.get_meta("Purchase Invoice").has_field(CHILD_TABLE_FIELD):
		lookup = _get_deduction_lookup(doc.company)
		_remove_deduction_taxes(doc, lookup["by_label"])
		return

	_migrate_taxes_to_child_table(doc)

	non_auto_rows = [
		row
		for row in doc.get(CHILD_TABLE_FIELD) or []
		if not row.get("is_weight_deduction") and not row.get("is_bag_deduction")
	]

	if non_auto_rows:
		_recalculate_child_table_amounts(doc)
	else:
		sync_weight_deduction_row(doc)


def _apply_deduction_rows_legacy(doc, deductions):
	lookup = _get_deduction_lookup(doc.company)
	_remove_deduction_taxes(doc, lookup["by_label"])


@frappe.whitelist()
def get_deduction_data(purchase_invoice):
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	ctx = _get_pi_context(pi)
	lookup = _get_deduction_lookup(pi.company)
	existing = _get_existing_deductions(pi, lookup)
	bag_rows = get_bag_rows(pi)

	result = []

	for dt in lookup["by_name"].values():
		if _should_skip_deduction(dt, pi):
			continue

		if (dt.deduction_type_name or "").strip() in AUTO_DEDUCTION_NAMES:
			continue

		if _uses_bag_wise_arrival(dt) and bag_rows:
			for bag in bag_rows:
				if not flt(bag["no_of_bags"]):
					continue
				saved = existing.get(
					_deduction_row_key(dt.name, bag["bag_type"], bag["no_of_bags"]),
					{},
				)
				result.append(_build_deduction_row(dt, ctx, saved, bag))
		elif dt.qty_deducation and dt.deduction_category == "multiple" and bag_rows:
			for bag in bag_rows:
				if not flt(bag["no_of_bags"]):
					continue
				saved = existing.get(
					_deduction_row_key(dt.name, bag["bag_type"], bag["no_of_bags"]),
					{},
				)
				result.append(_build_deduction_row(dt, ctx, saved, bag))
		else:
			saved = existing.get(_deduction_row_key(dt.name, "", 0), {})
			result.append(_build_deduction_row(dt, ctx, saved))

	bag_row = _build_bag_deduction_dialog_row(pi)
	if bag_row:
		result.append(bag_row)

	weight_row = _build_weight_deduction_dialog_row(pi)
	if weight_row:
		result.append(weight_row)

	return sorted(
		result,
		key=lambda row: (
			1 if row.get("is_bag_deduction") or row.get("is_weight_deduction") else 0,
			1 if row.get("is_weight_deduction") else 0,
			row["deduction_type_name"],
		),
	)


@frappe.whitelist()
def calculate_deduction_preview(purchase_invoice, deduction_type, actual, bag_type=None, no_of_bags=None):
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
		bag = _find_bag_row(get_bag_rows(pi), bag_type, no_of_bags=no_of_bags)

	row_ctx = _bag_context(ctx, bag) if bag else ctx
	amount, difference, required, mode = _resolve_amount(dt, row_ctx, actual=flt(actual))

	return {
		"actual": flt(actual),
		"required_value": required,
		"difference": difference,
		"amount": amount,
		"bag_type": bag_type or "",
		"no_of_bags": flt(row_ctx["total_bags"]) if bag else 0,
		"net_amount": row_ctx["net_amount"],
		"total_bags": row_ctx["total_bags"],
		"total_gross_weight": row_ctx["total_gross_weight"],
		"total_arrival_weight": row_ctx["total_arrival_weight"],
		"item_rate": row_ctx.get("item_rate", 0),
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
			item_rate=row_ctx.get("item_rate", 0),
		),
	}


@frappe.whitelist()
def apply_deductions(purchase_invoice, deductions):
	if isinstance(deductions, str):
		deductions = json.loads(deductions)

	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	if pi.docstatus == 1:
		frappe.throw(_("Cannot apply deductions on a submitted Purchase Invoice."))

	_set_child_table_from_deductions(pi, deductions)
	pi.save()

	return {"message": "Deductions applied successfully"}


def get_deduction_total(doc, exclude_auto_deductions=False):
	if frappe.get_meta("Purchase Invoice").has_field(CHILD_TABLE_FIELD) and doc.get(
		CHILD_TABLE_FIELD
	):
		total = 0
		for row in doc.get(CHILD_TABLE_FIELD) or []:
			if exclude_auto_deductions and _is_auto_deduction_row(row):
				continue
			total += flt(row.amount)
		return total

	return sum(
		flt(tax.tax_amount)
		for tax in doc.get("taxes") or []
		if tax.add_deduct_tax == "Deduct" and flt(tax.tax_amount) > 0
	)


def _is_auto_deduction_row(row):
	if row.get("is_bag_deduction") or row.get("is_weight_deduction"):
		return True

	deduction_type_name = (row.get("deduction_type_name") or "").split(" (")[0]
	return deduction_type_name in AUTO_DEDUCTION_NAMES


def get_deduction_item_code():
	settings_meta = frappe.get_meta("Kisan Master Settings", cached=True)
	if settings_meta.has_field("deduction_item"):
		item_code = frappe.db.get_single_value("Kisan Master Settings", "deduction_item")
		if item_code and frappe.db.exists("Item", item_code):
			return item_code

	if frappe.db.exists("Item", DEDUCTION_ITEM_CODE):
		return DEDUCTION_ITEM_CODE

	return None


def get_return_against_deduction_total(doc):
	if not doc.get("is_return") or not doc.get("return_against"):
		return 0

	if not frappe.db.exists("Purchase Invoice", doc.return_against):
		return 0

	source = frappe.get_doc("Purchase Invoice", doc.return_against)
	return flt(get_deduction_total(source, exclude_auto_deductions=True))


def remove_deduction_item_rows(doc):
	item_code = get_deduction_item_code()
	if not item_code:
		return

	for row in list(doc.get("items") or []):
		if row.item_code == item_code:
			doc.remove(row)


def sync_deduction_item_row(doc):
	if not frappe.get_meta("Purchase Invoice").has_field(CHILD_TABLE_FIELD):
		return

	if not doc.get("is_return"):
		remove_deduction_item_rows(doc)
		return

	item_code = get_deduction_item_code()
	deduction_total = get_return_against_deduction_total(doc)
	deduction_rows = _get_deduction_item_rows(doc, item_code) if item_code else []

	if deduction_total <= 0:
		for row in deduction_rows:
			doc.remove(row)
		return

	if not item_code:
		frappe.throw(
			_("Item {0} not found. Please create it to apply deductions on the invoice.").format(
				DEDUCTION_ITEM_CODE
			)
		)

	if deduction_rows:
		row = deduction_rows[0]
		_apply_deduction_item_values(doc, row, -1, deduction_total)
		for extra_row in deduction_rows[1:]:
			doc.remove(extra_row)
	else:
		item_row = doc.append(
			"items",
			{
				"item_code": item_code,
			},
		)
		_apply_deduction_item_values(doc, item_row, -1, deduction_total)


def _get_deduction_item_rows(doc, item_code):
	rows = [row for row in doc.get("items") or [] if row.item_code == item_code]

	if doc.get("is_return"):
		return rows

	return [row for row in rows if flt(row.qty) == -1]


def _apply_deduction_item_values(doc, item_row, qty, rate):
	from erpnext.stock.get_item_details import get_item_details

	qty = flt(qty)
	rate = flt(rate)

	parent_dict = {fieldname: doc.get(fieldname) for fieldname in doc.meta.get_valid_columns()}
	args = parent_dict.copy()
	args.update(item_row.as_dict())
	args.update(
		{
			"doctype": doc.doctype,
			"name": doc.name,
			"child_doctype": item_row.doctype,
			"child_docname": item_row.name,
			"item_code": item_row.item_code,
			"qty": qty,
			"rate": rate,
		}
	)

	item_details = get_item_details(args, doc, for_validate=False, overwrite_warehouse=False)
	for fieldname, value in item_details.items():
		if item_row.meta.get_field(fieldname) and value is not None and item_row.get(fieldname) is None:
			item_row.set(fieldname, value)

	item_row.qty = qty
	item_row.rate = rate
	item_row.received_qty = qty

	conversion_factor = flt(item_row.conversion_factor) or 1
	item_row.conversion_factor = conversion_factor
	item_row.stock_qty = qty * conversion_factor

	conversion_rate = flt(doc.conversion_rate) or 1
	item_row.amount = qty * rate
	item_row.base_rate = rate * conversion_rate
	item_row.base_amount = item_row.amount * conversion_rate

	if item_row.meta.has_field("net_rate"):
		item_row.net_rate = rate
	if item_row.meta.has_field("net_amount"):
		item_row.net_amount = item_row.amount
	if item_row.meta.has_field("base_net_rate"):
		item_row.base_net_rate = item_row.base_rate
	if item_row.meta.has_field("base_net_amount"):
		item_row.base_net_amount = item_row.base_amount


def _set_deduction_item_details(doc, item_row):
	_apply_deduction_item_values(doc, item_row, item_row.qty, item_row.rate)
