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


def _get_commodity_accepted_kg(source):
	deduction_item_code = get_deduction_item_code()
	accepted_kg = 0

	for item in source.get("items") or []:
		if deduction_item_code and item.item_code == deduction_item_code:
			continue
		accepted_kg += flt(item.qty) * 100

	return accepted_kg


def _get_return_qty_quintal_for_item(source_qty_quintal, weight_ded_kg, accepted_kg):
	"""Multi-rate sauda: weight deduction split item-wise by accepted qty share."""
	if not source_qty_quintal or not weight_ded_kg or not accepted_kg:
		return 0

	return flt((weight_ded_kg / accepted_kg) * flt(source_qty_quintal), 3)


def _set_item_qty_from_weight_deduction(doc, source, weight_ded_kg):
	weight_ded_kg = flt(weight_ded_kg)
	if not weight_ded_kg or not doc.get("items"):
		return

	accepted_kg = _get_commodity_accepted_kg(source)
	if not accepted_kg:
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

	for item in commodity_items:
		source_item = source_items.get(item.purchase_invoice_item)
		source_qty = flt(source_item.qty) if source_item else 0
		return_qty_quintal = _get_return_qty_quintal_for_item(
			source_qty, weight_ded_kg, accepted_kg
		)
		if not return_qty_quintal:
			continue

		qty = -return_qty_quintal
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
