# Copyright (c) 2026, Hidayatali and contributors

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
	make_debit_note as erpnext_make_debit_note,
)
from frappe.utils import flt

from kisan_customization.broker_commission.service import clear_broker_commission_fields
from kisan_customization.purchase_invoice.deductions import (
	_calculate_weight_deduction_amount,
	get_deduction_item_code,
	sync_deduction_item_row,
)


@frappe.whitelist()
def make_debit_note(source_name, target_doc=None):
	doc = erpnext_make_debit_note(source_name, target_doc)
	source = frappe.get_doc("Purchase Invoice", source_name)
	_apply_debit_note_settings(doc, source)
	return doc


def _apply_debit_note_settings(doc, source):
	doc.is_return = 1
	doc.return_against = source.name
	doc.update_outstanding_for_self = 1
	doc.update_billed_amount_in_purchase_order = 0
	doc.update_billed_amount_in_purchase_receipt = 1

	weight_deduction_kg = _get_weight_deduction_kg(source)
	if doc.meta.has_field("custom_weight_deduction"):
		doc.custom_weight_deduction = weight_deduction_kg

	if weight_deduction_kg > 0:
		_set_item_qty_from_weight_deduction(doc, source, weight_deduction_kg)

	clear_broker_commission_fields(doc)
	sync_deduction_item_row(doc)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def _get_weight_deduction_kg(source):
	weight_deduction_kg = flt(source.get("custom_weight_deduction"))
	if weight_deduction_kg:
		return weight_deduction_kg

	weight_deduction_kg, _, _ = _calculate_weight_deduction_amount(source)
	return flt(weight_deduction_kg)


def _set_item_qty_from_weight_deduction(doc, source, weight_deduction_kg):
	return_qty_quintal = flt(weight_deduction_kg / 100, 3)
	if not return_qty_quintal or not doc.get("items"):
		return

	deduction_item_code = get_deduction_item_code()
	source_items = {item.name: item for item in source.get("items") or []}
	commodity_items = [
		item
		for item in doc.get("items") or []
		if not deduction_item_code or item.item_code != deduction_item_code
	]
	if not commodity_items:
		return

	total_source_qty = sum(
		flt(source_items.get(item.purchase_invoice_item).qty)
		for item in commodity_items
		if source_items.get(item.purchase_invoice_item)
	)

	for item in commodity_items:
		source_item = source_items.get(item.purchase_invoice_item)
		source_qty = flt(source_item.qty) if source_item else 0

		if total_source_qty:
			share = source_qty / total_source_qty
		else:
			share = 1 / len(commodity_items)

		qty = -flt(return_qty_quintal * share, 3)
		item.qty = qty
		item.received_qty = qty

		conversion_factor = flt(item.conversion_factor) or 1
		item.stock_qty = qty * conversion_factor
		_refresh_return_item_amounts(doc, item)


def _refresh_return_item_amounts(doc, item):
	conversion_rate = flt(doc.conversion_rate) or 1
	item.amount = flt(item.qty) * flt(item.rate)
	item.base_rate = flt(item.rate) * conversion_rate
	item.base_amount = item.amount * conversion_rate
