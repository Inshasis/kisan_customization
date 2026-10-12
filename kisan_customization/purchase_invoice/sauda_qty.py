# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

QUINTAL_TO_KG = 100


def validate_sauda_qty_range(doc):
	if doc.get("is_return"):
		return

	if not frappe.db.has_column("Purchase Order", "custom_sauda_qty_from"):
		return

	purchase_orders = {
		row.get("purchase_order")
		for row in doc.get("items") or []
		if row.get("purchase_order")
	}

	for purchase_order in purchase_orders:
		qty_from, qty_to = _get_sauda_qty_range(purchase_order)
		if not qty_from and not qty_to:
			continue

		gross_kg = _gross_kg_for_purchase_order(doc, purchase_order)

		min_kg = flt(qty_from) * QUINTAL_TO_KG if qty_from else 0
		max_kg = flt(qty_to) * QUINTAL_TO_KG if qty_to else 0

		if qty_from and gross_kg < min_kg:
			frappe.throw(
				_(
					"Gross Weight ({0} Kg) for Purchase Order {1} cannot be less than Sauda Qty From {2} quintal ({3} Kg)."
				).format(gross_kg, purchase_order, qty_from, min_kg)
			)

		if qty_to and gross_kg > max_kg:
			frappe.throw(
				_(
					"Gross Weight ({0} Kg) for Purchase Order {1} cannot be greater than Sauda Qty To {2} quintal ({3} Kg)."
				).format(gross_kg, purchase_order, qty_to, max_kg)
			)


def _gross_kg_for_purchase_order(doc, purchase_order):
	"""Sum item-line Gross Weight (Kg) for PI rows linked to this PO only."""
	from kisan_customization.purchase_invoice.item_gross_weight import (
		get_commodity_items,
		get_item_line_gross_weight_kg,
	)

	total = 0.0
	for row in get_commodity_items(doc):
		if row.get("purchase_order") != purchase_order:
			continue
		total += get_item_line_gross_weight_kg(row)
	return flt(total)


def _get_sauda_qty_range(purchase_order):
	po_range = frappe.db.get_value(
		"Purchase Order",
		purchase_order,
		["custom_sauda_qty_from", "custom_sauda_qty_to"],
		as_dict=True,
	)
	if not po_range:
		return 0, 0

	return flt(po_range.custom_sauda_qty_from), flt(po_range.custom_sauda_qty_to)
