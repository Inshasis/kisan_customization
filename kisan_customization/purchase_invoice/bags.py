# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_bag_type_options():
	settings = frappe.get_single("Kisan Master Settings")
	return [
		{"bag_type": row.bag_type, "charges": flt(row.charges)}
		for row in settings.get("bag_wise_deductions") or []
		if row.bag_type
	]


@frappe.whitelist()
def get_bag_charges(bag_type):
	for row in get_bag_type_options():
		if row["bag_type"] == bag_type:
			return flt(row["charges"])
	return 0


def get_pi_avg_rate(doc):
	rates = [flt(row.rate) for row in doc.get("items") or [] if flt(row.rate)]
	if not rates:
		return 0
	return flt(sum(rates) / len(rates))


def get_pi_item_rate(doc):
	return get_pi_avg_rate(doc)


def get_accepted_qty_kg(doc):
	from kisan_customization.utils.deduction_utils import get_pi_total_qty

	return flt(get_pi_total_qty(doc)) * 100


def calculate_bag_deduction(doc):
	from kisan_customization.utils.deduction_utils import (
		get_pi_total_arrival_weight,
		get_pi_total_gross_weight,
	)

	gross_weight = get_pi_total_gross_weight(doc)
	arrival_weight = get_pi_total_arrival_weight(doc)
	bag_deduction = max(0, flt(gross_weight) - flt(arrival_weight))
	item_rate = get_pi_item_rate(doc)
	amount = flt(bag_deduction * item_rate / 100, 2)
	return bag_deduction, item_rate, amount


def calculate_weight_deduction(doc):
	from kisan_customization.utils.deduction_utils import get_pi_total_gross_weight

	accepted_qty_kg = get_accepted_qty_kg(doc)
	gross_weight = get_pi_total_gross_weight(doc)
	weight_deduction = max(0, flt(accepted_qty_kg) - flt(gross_weight))
	item_rate = get_pi_item_rate(doc)
	amount = flt(weight_deduction * item_rate / 100, 2)
	return weight_deduction, item_rate, amount


def get_child_bag_sum(doc):
	return sum(flt(row.no_of_bags) for row in doc.get("custom_bag_details") or [])


def get_plastic_gross_weight(doc):
	total = 0
	for row in doc.get("custom_bag_details") or []:
		if (row.bag_type or "").lower() == "plastic":
			total += flt(row.gross_weight_kg)
	return total


def has_plastic_bag(doc):
	return any(
		(row.bag_type or "").lower() == "plastic" and flt(row.no_of_bags)
		for row in doc.get("custom_bag_details") or []
	)


def get_bag_rows(doc):
	rate = get_pi_item_rate(doc)
	rows = []

	for row in doc.get("custom_bag_details") or []:
		arrival = flt(row.arrival_qty_kg)
		gross = flt(row.gross_weight_kg)
		rows.append(
			{
				"bag_type": row.bag_type,
				"no_of_bags": flt(row.no_of_bags),
				"charges": flt(row.charges),
				"gross_weight_kg": gross,
				"deduct_weight_kg": flt(row.deduct_weight_kg),
				"arrival_qty_kg": arrival,
				"bag_line_amount": (arrival * rate) / 100,
			}
		)

	return rows


def get_bag_total_amount(doc):
	return sum(row["bag_line_amount"] for row in get_bag_rows(doc))


def validate_bag_details(doc):
	if not doc.get("custom_bag_details"):
		return

	total_bags = flt(doc.custom_total_bags)
	if not total_bags:
		frappe.throw(_("Please enter Total Bags before filling Bag Details."))

	child_sum = get_child_bag_sum(doc)
	if not child_sum:
		return

	if child_sum != total_bags:
		frappe.throw(
			_("Sum of No. of Bags ({0}) must equal Total Bags ({1}).").format(
				int(child_sum), int(total_bags)
			)
		)


def recalculate_bag_weights(doc):
	total_bags = flt(doc.custom_total_bags)
	total_gross = flt(doc.custom_total_gross_weight)

	if not total_bags:
		return

	average_weight = total_gross / total_bags if total_gross else 0
	total_arrival = 0

	for row in doc.get("custom_bag_details") or []:
		bags = flt(row.no_of_bags)
		charges = flt(row.charges)
		row.deduct_weight_kg = bags * charges
		row.gross_weight_kg = bags * average_weight
		row.arrival_qty_kg = max(0, flt(row.gross_weight_kg) - flt(row.deduct_weight_kg))
		total_arrival += flt(row.arrival_qty_kg)

	doc.custom_total_arrival_weight = total_arrival
	_sync_bag_deduction_header(doc)


def _sync_bag_deduction_header(doc):
	if not doc.meta.has_field("custom_bag_deduction"):
		return

	bag_deduction, avg_rate, amount = calculate_bag_deduction(doc)
	doc.custom_bag_deduction = bag_deduction
	if doc.meta.has_field("custom_bag_deduction_amount"):
		doc.custom_bag_deduction_amount = amount
	if doc.meta.has_field("custom_weight_deduction"):
		weight_deduction, _, weight_amount = calculate_weight_deduction(doc)
		doc.custom_weight_deduction = weight_deduction
		if doc.meta.has_field("custom_weight_deduction_amount"):
			doc.custom_weight_deduction_amount = weight_amount
