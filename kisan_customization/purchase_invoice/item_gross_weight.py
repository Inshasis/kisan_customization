# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt

QUINTAL_TO_KG = 100


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


def _pi_item_field_by_label(label):
	meta = frappe.get_meta("Purchase Invoice Item")
	for df in meta.fields:
		if (df.label or "").strip() == label:
			return df.fieldname
	return None


def get_pi_item_weight_deduction_fieldnames():
	"""Use existing Custom Fields on Purchase Invoice Item (no patch creates them)."""
	meta = frappe.get_meta("Purchase Invoice Item")
	kg_field = None
	amount_field = None

	if meta.has_field("custom_weight_deduction_kg"):
		kg_field = "custom_weight_deduction_kg"
	else:
		kg_field = _pi_item_field_by_label("Weight Deduction (kg)")

	if meta.has_field("custom_weight_deduction_amount"):
		amount_field = "custom_weight_deduction_amount"
	else:
		amount_field = _pi_item_field_by_label("Weight Deduction Amount")

	return kg_field, amount_field


def get_item_line_weight_deduction_kg(item):
	"""Accepted qty (kg) − line gross: qty (quintal) × 100 − custom_gross_weight_kg."""
	return flt(flt(item.get("qty")) * QUINTAL_TO_KG - get_item_line_gross_weight_kg(item))


def get_item_line_weight_deduction_amount(item):
	"""Line weight deduction (kg) × line rate (rate is per quintal)."""
	line_kg = get_item_line_weight_deduction_kg(item)
	return flt(line_kg * flt(item.get("rate")) / QUINTAL_TO_KG, 2)


def sync_item_weight_deductions(doc):
	"""Per commodity item row → sum into PI Weight Deduction (kg) / Amount."""
	if doc.get("is_return"):
		return
	if not doc.meta.has_field("custom_weight_deduction"):
		return

	kg_field, amount_field = get_pi_item_weight_deduction_fieldnames()
	if not kg_field:
		return

	total_kg = 0.0
	total_amount = 0.0

	for row in get_commodity_items(doc):
		line_kg = get_item_line_weight_deduction_kg(row)
		line_amount = get_item_line_weight_deduction_amount(row)
		row.set(kg_field, line_kg)
		if amount_field:
			row.set(amount_field, line_amount)
		total_kg += line_kg
		total_amount += line_amount

	doc.custom_weight_deduction = flt(total_kg)
	if doc.meta.has_field("custom_weight_deduction_amount"):
		doc.custom_weight_deduction_amount = flt(total_amount, 2)
