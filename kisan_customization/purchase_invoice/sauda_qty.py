# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt


def validate_sauda_qty_range(doc):
	if doc.get("is_return"):
		return

	if not frappe.db.has_column("Purchase Order", "custom_sauda_qty_from"):
		return

	for item in doc.get("items") or []:
		if not item.get("purchase_order"):
			continue

		qty_from, qty_to = _get_sauda_qty_range(item.purchase_order)
		if not qty_from and not qty_to:
			continue

		qty = flt(item.qty)
		if qty_from and qty < qty_from:
			frappe.throw(
				_(
					"Row #{0}: Qty {1} cannot be less than Sauda Qty From {2} for Purchase Order {3}"
				).format(item.idx, qty, qty_from, item.purchase_order)
			)

		if qty_to and qty > qty_to:
			frappe.throw(
				_(
					"Row #{0}: Qty {1} cannot be greater than Sauda Qty To {2} for Purchase Order {3}"
				).format(item.idx, qty, qty_to, item.purchase_order)
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
