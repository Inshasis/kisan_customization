# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt


def _get_deduction_item_code():
	settings_meta = frappe.get_meta("Kisan Master Settings", cached=True)
	if settings_meta.has_field("deduction_item"):
		item_code = frappe.db.get_single_value("Kisan Master Settings", "deduction_item")
		if item_code and frappe.db.exists("Item", item_code):
			return item_code
	return None


def get_item_line_gross_weight_kg(item):
	return flt(item.get("custom_gross_weight_kg"))


def get_commodity_items(doc):
	deduction_item_code = _get_deduction_item_code()
	return [
		row
		for row in doc.get("items") or []
		if not deduction_item_code or row.item_code != deduction_item_code
	]


def get_pi_weighted_item_rate(doc):
	"""Weighted average rate by manually entered gross weight (kg) per item line."""
	total_gross = 0
	weighted_sum = 0

	for row in get_commodity_items(doc):
		gross = get_item_line_gross_weight_kg(row)
		rate = flt(row.rate)
		if gross <= 0 or rate <= 0:
			continue
		total_gross += gross
		weighted_sum += gross * rate

	if total_gross:
		return flt(weighted_sum / total_gross)

	from kisan_customization.purchase_invoice.bags import get_pi_avg_rate

	return get_pi_avg_rate(doc)


def get_gross_weight_share(item, doc):
	"""Share of total PI gross weight for one item line (multi-rate splits)."""
	total = sum(get_item_line_gross_weight_kg(row) for row in get_commodity_items(doc))
	line = get_item_line_gross_weight_kg(item)
	if total and line:
		return line / total
	return 0


def get_items_gross_weight_total(doc):
	return sum(get_item_line_gross_weight_kg(row) for row in get_commodity_items(doc))


def sync_total_gross_weight_from_items(doc):
	"""Total Gross Weight (kg) = sum of item line Gross Weight (Kg)."""
	if doc.get("is_return"):
		return
	if not doc.meta.has_field("custom_total_gross_weight"):
		return
	doc.custom_total_gross_weight = flt(get_items_gross_weight_total(doc))


def validate_item_gross_weights(doc):
	sync_total_gross_weight_from_items(doc)
