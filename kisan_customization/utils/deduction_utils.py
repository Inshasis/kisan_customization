# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

FORMULA_VARIABLES = (
	"net_amount",
	"total_amount",
	"total_bags",
	"total_qty",
	"total_gross_weight",
	"total_arrival_weight",
	"plastic_gross_weight",
	"charges_per_unit",
	"charges",
	"required_value",
	"actual",
	"difference",
	"item_rate",
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


def get_pi_total_gross_weight(doc):
	if doc.get("custom_total_gross_weight"):
		return flt(doc.custom_total_gross_weight)
	return sum(flt(row.gross_weight_kg) for row in doc.get("custom_bag_details") or [])


def get_pi_total_arrival_weight(doc):
	if doc.get("custom_total_arrival_weight"):
		return flt(doc.custom_total_arrival_weight)
	return sum(flt(row.arrival_qty_kg) for row in doc.get("custom_bag_details") or [])


def get_pi_plastic_gross_weight(doc):
	from kisan_customization.purchase_invoice.bags import get_plastic_gross_weight

	return get_plastic_gross_weight(doc)


def get_calculation_mode(dt):
	if dt.qty_deducation:
		return "qty_deducation"
	if (dt.calculation or "").strip():
		return "formula"
	if flt(dt.charges_per_unit):
		return "direct"
	return "manual"


def get_formula_context(
	dt,
	net_amount=0,
	total_qty=0,
	total_bags=0,
	total_gross_weight=0,
	total_arrival_weight=0,
	plastic_gross_weight=0,
	actual=0,
	difference=0,
	item_rate=0,
):
	charges = flt(dt.charges_per_unit)
	net_amount = flt(net_amount)

	return {
		"net_amount": net_amount,
		"total_amount": net_amount,
		"total_bags": flt(total_bags),
		"total_qty": flt(total_qty),
		"total_gross_weight": flt(total_gross_weight),
		"total_arrival_weight": flt(total_arrival_weight),
		"plastic_gross_weight": flt(plastic_gross_weight),
		"charges_per_unit": charges,
		"charges": charges,
		"required_value": flt(dt.required_value),
		"actual": flt(actual),
		"difference": flt(difference),
		"item_rate": flt(item_rate),
	}


def evaluate_calculation(
	dt,
	net_amount=0,
	total_qty=0,
	total_bags=0,
	total_gross_weight=0,
	total_arrival_weight=0,
	plastic_gross_weight=0,
	actual=0,
	difference=0,
	item_rate=0,
):
	formula = (dt.calculation or "").strip()
	if not formula:
		return 0

	context = get_formula_context(
		dt,
		net_amount,
		total_qty,
		total_bags,
		total_gross_weight,
		total_arrival_weight,
		plastic_gross_weight,
		actual,
		difference,
		item_rate,
	)

	try:
		return flt(frappe.safe_eval(formula, None, context))
	except Exception as exc:
		frappe.throw(
			_("Invalid calculation in Deduction Type {0}: {1}").format(
				getattr(dt, "deduction_type_name", dt), str(exc)
			)
		)


def get_calculation_formula(
	dt,
	total_bags=0,
	net_amount=0,
	total_qty=0,
	total_gross_weight=0,
	total_arrival_weight=0,
	plastic_gross_weight=0,
	actual=0,
	difference=0,
	item_rate=0,
):
	mode = get_calculation_mode(dt)
	calc_kwargs = {
		"net_amount": net_amount,
		"total_qty": total_qty,
		"total_bags": total_bags,
		"total_gross_weight": total_gross_weight,
		"total_arrival_weight": total_arrival_weight,
		"plastic_gross_weight": plastic_gross_weight,
		"actual": actual,
		"difference": difference,
		"item_rate": item_rate,
	}

	if mode == "qty_deducation":
		if (dt.calculation or "").strip():
			amount = evaluate_calculation(dt, **calc_kwargs)
			return f"{dt.calculation.strip()} = {amount}"
		return _("Actual − Required → then apply default amount formula")

	if mode == "formula":
		amount = evaluate_calculation(dt, **calc_kwargs)
		return f"{dt.calculation.strip()} = {amount}"

	if mode == "direct":
		return str(flt(dt.charges_per_unit))

	return _("Enter amount manually")


def get_tier_multiplier(value):
	settings = frappe.get_single("Kisan Master Settings")
	value = flt(value)

	for row in sorted(
		settings.get("deduction_tier_range") or [],
		key=lambda tier: flt(tier.range_from),
	):
		if flt(row.range_from) <= value <= flt(row.range_to):
			return flt(row.multiplier)

	return 1.0


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


def _calculate_difference(dt, actual):
	required = flt(dt.required_value)
	actual = flt(actual)

	if actual <= required:
		return 0

	if dt.tiered_calculation:
		return calculate_tiered_difference(actual, required)

	return max(0, actual - required) * get_tier_multiplier(actual)


def _calculate_qty_amount_fallback(dt, difference, net_amount, total_qty):
	if dt.tiered_calculation or (
		dt.deduction_category == "multiple" and not flt(dt.charges_per_unit)
	):
		return (net_amount / 100) * difference

	if dt.deduction_category == "multiple":
		return (difference * flt(dt.charges_per_unit) * total_qty) / 100

	return (flt(dt.charges_per_unit) * total_qty) / 100 if total_qty else flt(dt.charges_per_unit)


def calculate_qty_deducation_amount(
	dt,
	actual,
	net_amount,
	total_qty,
	total_bags=0,
	total_gross_weight=0,
	total_arrival_weight=0,
	plastic_gross_weight=0,
	item_rate=0,
):
	actual = flt(actual)
	required = flt(dt.required_value)
	net_amount = flt(net_amount)
	total_qty = flt(total_qty)
	total_bags = flt(total_bags)
	total_gross_weight = flt(total_gross_weight)
	total_arrival_weight = flt(total_arrival_weight)
	plastic_gross_weight = flt(plastic_gross_weight)
	item_rate = flt(item_rate)

	difference = _calculate_difference(dt, actual)

	if difference <= 0:
		return 0, difference, required

	if (dt.calculation or "").strip():
		amount = evaluate_calculation(
			dt,
			net_amount=net_amount,
			total_qty=total_qty,
			total_bags=total_bags,
			total_gross_weight=total_gross_weight,
			total_arrival_weight=total_arrival_weight,
			plastic_gross_weight=plastic_gross_weight,
			actual=actual,
			difference=difference,
			item_rate=item_rate,
		)
	else:
		amount = _calculate_qty_amount_fallback(dt, difference, net_amount, total_qty)

	return flt(amount), flt(difference), required


def calculate_deduction_amount(
	dt,
	actual=0,
	net_amount=0,
	total_qty=0,
	total_bags=0,
	total_gross_weight=0,
	total_arrival_weight=0,
	plastic_gross_weight=0,
	manual_amount=0,
	item_rate=0,
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
	total_gross_weight = flt(total_gross_weight)
	total_arrival_weight = flt(total_arrival_weight)
	plastic_gross_weight = flt(plastic_gross_weight)
	item_rate = flt(item_rate)

	if mode == "qty_deducation":
		return calculate_qty_deducation_amount(
			dt,
			actual,
			net_amount,
			total_qty,
			total_bags,
			total_gross_weight,
			total_arrival_weight,
			plastic_gross_weight,
			item_rate,
		)

	if mode == "formula":
		difference = max(0, flt(actual) - flt(dt.required_value))
		amount = evaluate_calculation(
			dt,
			net_amount=net_amount,
			total_qty=total_qty,
			total_bags=total_bags,
			total_gross_weight=total_gross_weight,
			total_arrival_weight=total_arrival_weight,
			plastic_gross_weight=plastic_gross_weight,
			actual=actual,
			difference=difference,
			item_rate=item_rate,
		)
		return flt(amount), difference, flt(dt.required_value)

	if mode == "direct":
		return flt(dt.charges_per_unit), 0, flt(dt.required_value)

	return flt(manual_amount), 0, flt(dt.required_value)
