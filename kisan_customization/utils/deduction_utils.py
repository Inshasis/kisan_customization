# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

FORMULA_VARIABLES = (
	"net_amount",
	"total_bags",
	"total_qty",
	"charges_per_unit",
	"required_value",
	"actual",
	"difference",
)


def get_bag_charges(bag_type):
	settings = frappe.get_single("Kisan Master Settings")

	for row in settings.get("bag_wise_deductions") or []:
		if row.bag_type == bag_type:
			return flt(row.charges)

	return 0.0


def get_pi_total_qty(doc):
	return sum(flt(row.qty) for row in doc.get("items") or [])


def get_pi_net_amount(doc):
	if doc.get("total"):
		return flt(doc.total)
	return sum(flt(row.amount) for row in doc.get("items") or [])


def get_pi_total_bags(doc):
	return flt(doc.get("custom_total_bags"))


def get_calculation_mode(dt):
	if dt.qty_deducation:
		return "qty_deducation"
	if (dt.calculation or "").strip():
		return "formula"
	if flt(dt.charges_per_unit):
		return "direct"
	return "manual"


def get_formula_context(dt, net_amount=0, total_qty=0, total_bags=0, actual=0, difference=0):
	return {
		"net_amount": flt(net_amount),
		"total_bags": flt(total_bags),
		"total_qty": flt(total_qty),
		"charges_per_unit": flt(dt.charges_per_unit),
		"required_value": flt(dt.required_value),
		"actual": flt(actual),
		"difference": flt(difference),
	}


def evaluate_calculation(
	dt, net_amount=0, total_qty=0, total_bags=0, actual=0, difference=0
):
	formula = (dt.calculation or "").strip()
	if not formula:
		return 0

	context = get_formula_context(dt, net_amount, total_qty, total_bags, actual, difference)

	try:
		return flt(frappe.safe_eval(formula, None, context))
	except Exception as exc:
		frappe.throw(
			_("Invalid calculation in Deduction Type {0}: {1}").format(
				getattr(dt, "deduction_type_name", dt), str(exc)
			)
		)


def get_calculation_formula(
	dt, total_bags=0, net_amount=0, total_qty=0, actual=0, difference=0
):
	mode = get_calculation_mode(dt)

	if mode == "qty_deducation":
		return _("Actual − Required → Net Amount / 100 × Difference")

	if mode == "formula":
		amount = evaluate_calculation(
			dt,
			net_amount=net_amount,
			total_qty=total_qty,
			total_bags=total_bags,
			actual=actual,
			difference=difference,
		)
		return f"{dt.calculation.strip()} = {amount}"

	if mode == "direct":
		return str(flt(dt.charges_per_unit))

	return _("Enter amount manually")


def calculate_tiered_difference(actual, required):
	settings = frappe.get_single("Kisan Master Settings")
	tier_ranges = sorted(
		settings.get("deduction_tier_range") or [],
		key=lambda row: flt(row.range_from),
	)

	actual = flt(actual)
	required = flt(required)

	if actual <= required or not tier_ranges:
		return max(0, actual - required)

	total_weighted_diff = 0

	for index, tier in enumerate(tier_ranges):
		tier_start = flt(tier.range_from)
		tier_end = flt(tier.range_to)

		if actual <= tier_start:
			break

		range_start = max(tier_start, required) if index == 0 else tier_start
		range_end = min(tier_end, actual)

		if range_end > range_start:
			total_weighted_diff += (range_end - range_start) * flt(tier.multiplier)

	return total_weighted_diff


def calculate_qty_deducation_amount(dt, actual, net_amount, total_qty):
	actual = flt(actual)
	required = flt(dt.required_value)
	net_amount = flt(net_amount)
	total_qty = flt(total_qty)

	if dt.tiered_calculation:
		difference = calculate_tiered_difference(actual, required)
	elif dt.deduction_category == "multiple":
		difference = max(0, actual - required)
	else:
		difference = max(0, actual - required)

	if difference <= 0:
		return 0, difference, required

	if dt.tiered_calculation or (
		dt.deduction_category == "multiple" and not flt(dt.charges_per_unit)
	):
		amount = (net_amount / 100) * difference
	elif dt.deduction_category == "multiple":
		amount = (difference * flt(dt.charges_per_unit) * total_qty) / 100
	else:
		amount = (flt(dt.charges_per_unit) * total_qty) / 100 if total_qty else flt(dt.charges_per_unit)

	return flt(amount), flt(difference), required


def calculate_deduction_amount(
	dt, actual=0, net_amount=0, total_qty=0, total_bags=0, manual_amount=0
):
	if isinstance(dt, str):
		dt = frappe.get_cached_value(
			"Deduction Type",
			dt,
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
		if not dt:
			return 0, 0, 0

	mode = get_calculation_mode(dt)
	net_amount = flt(net_amount)
	total_qty = flt(total_qty)
	total_bags = flt(total_bags)

	if mode == "qty_deducation":
		return calculate_qty_deducation_amount(dt, actual, net_amount, total_qty)

	if mode == "formula":
		difference = max(0, flt(actual) - flt(dt.required_value))
		amount = evaluate_calculation(
			dt,
			net_amount=net_amount,
			total_qty=total_qty,
			total_bags=total_bags,
			actual=actual,
			difference=difference,
		)
		return flt(amount), difference, flt(dt.required_value)

	if mode == "direct":
		return flt(dt.charges_per_unit), 0, flt(dt.required_value)

	return flt(manual_amount), 0, flt(dt.required_value)
