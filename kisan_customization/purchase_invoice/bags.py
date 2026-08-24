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


def get_pi_item_rate(doc):
	if doc.get("items"):
		return flt(doc.items[0].rate)
	return 0


def sync_arrival_qty_to_items(doc):
	arrival_weight = flt(doc.get("custom_total_arrival_weight"))
	if not arrival_weight:
		return

	qty = flt(arrival_weight / 100, 3)
	for item in doc.get("items") or []:
		item.qty = qty
		item.amount = flt(qty) * flt(item.rate)


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
