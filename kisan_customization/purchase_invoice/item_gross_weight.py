# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

from kisan_customization.utils.deduction_utils import get_pi_total_gross_weight


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


def validate_item_gross_weights(doc):
	if doc.get("is_return"):
		return

	lines = [get_item_line_gross_weight_kg(row) for row in get_commodity_items(doc) if flt(row.rate)]
	if not any(lines):
		return

	line_total = sum(lines)
	header_gross = get_pi_total_gross_weight(doc)
	if not header_gross or not line_total:
		return

	if abs(line_total - header_gross) > 0.5:
		frappe.throw(
			_(
				"Sum of item Gross Weight (Kg) ({0}) must match Total Gross Weight ({1}) on the invoice."
			).format(line_total, header_gross)
		)
