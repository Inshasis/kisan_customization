# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

from kisan_customization.utils.deduction_utils import get_pi_total_gross_weight

QUINTAL_TO_KG = 100


def validate_sauda_qty_range(doc):
	if doc.get("is_return"):
		return

	if not frappe.db.has_column("Purchase Order", "custom_sauda_qty_from"):
		return

	gross_kg = flt(get_pi_total_gross_weight(doc))
	if not gross_kg:
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

		min_kg = flt(qty_from) * QUINTAL_TO_KG if qty_from else 0
		max_kg = flt(qty_to) * QUINTAL_TO_KG if qty_to else 0

		if qty_from and gross_kg < min_kg:
			frappe.throw(
				_(
					"Total Gross Weight ({0} Kg) cannot be less than Sauda Qty From {1} quintal ({2} Kg) for Purchase Order {3}."
				).format(gross_kg, qty_from, min_kg, purchase_order)
			)

		if qty_to and gross_kg > max_kg:
			frappe.throw(
				_(
					"Total Gross Weight ({0} Kg) cannot be greater than Sauda Qty To {1} quintal ({2} Kg) for Purchase Order {3}."
				).format(gross_kg, qty_to, max_kg, purchase_order)
			)


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
