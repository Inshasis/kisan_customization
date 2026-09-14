# Copyright (c) 2026, Hidayatali and contributors

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
	make_debit_note as erpnext_make_debit_note,
)
from frappe import _
from frappe.utils import flt

from kisan_customization.broker_commission.service import clear_broker_commission_fields
from kisan_customization.purchase_invoice.deductions import (
	_calculate_bag_deduction_amount,
	_calculate_weight_deduction_amount,
	get_deduction_item_code,
	sync_deduction_item_row,
)

WEIGHT_CONTEXT_FIELDS = (
	"custom_total_bags",
	"custom_total_gross_weight",
	"custom_total_arrival_weight",
)


def get_active_debit_note(purchase_invoice, exclude_name=None):
	if not purchase_invoice:
		return None

	filters = {
		"return_against": purchase_invoice,
		"is_return": 1,
		"docstatus": ("<", 2),
	}
	if exclude_name:
		filters["name"] = ("!=", exclude_name)

	return frappe.db.get_value("Purchase Invoice", filters, "name")


@frappe.whitelist()
def has_active_debit_note(purchase_invoice):
	return bool(get_active_debit_note(purchase_invoice))


def validate_unique_debit_note(doc):
	if not doc.get("is_return") or not doc.get("return_against"):
		return

	existing = get_active_debit_note(doc.return_against, exclude_name=doc.name)
	if not existing:
		return

	frappe.throw(
		_("Debit Note {0} already exists against Purchase Invoice {1}. Cancel it before creating another.").format(
			frappe.bold(existing),
			frappe.bold(doc.return_against),
		),
		title=_("Duplicate Debit Note"),
	)


@frappe.whitelist()
def make_debit_note(source_name, target_doc=None):
	existing = get_active_debit_note(source_name)
	if existing:
		frappe.throw(
			_("Debit Note {0} already exists against this Purchase Invoice.").format(
				frappe.bold(existing)
			),
			title=_("Duplicate Debit Note"),
		)

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

	_copy_weight_context_from_source(doc, source)

	weight_kg, bag_kg, weight_amt, bag_amt = _calculate_return_deductions(source)
	_sync_return_deduction_fields(doc, weight_kg, bag_kg, weight_amt, bag_amt)

	# Commodity lines: Weight + Bag deduction (kg) → quintal (÷ 100), split by item qty %.
	return_kg = flt(weight_kg) + flt(bag_kg)
	if return_kg > 0:
		_set_item_qty_from_deduction_kg(doc, source, return_kg)

	clear_broker_commission_fields(doc)
	# Quality & Other: other deduction amounts only (not bag/weight auto rows).
	sync_deduction_item_row(doc)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def _calculate_return_deductions(source):
	"""Always recalculate from source PI (total qty × 100 − gross weight, bag gross − arrival)."""
	weight_kg, _, weight_amt = _calculate_weight_deduction_amount(source)
	bag_kg, _, bag_amt = _calculate_bag_deduction_amount(source)
	return flt(weight_kg), flt(bag_kg), flt(weight_amt), flt(bag_amt)


def _copy_weight_context_from_source(doc, source):
	for fieldname in WEIGHT_CONTEXT_FIELDS:
		if not doc.meta.has_field(fieldname):
			continue
		if source.get(fieldname) is not None:
			doc.set(fieldname, source.get(fieldname))


def _sync_return_deduction_fields(doc, weight_kg, bag_kg, weight_amt=0, bag_amt=0):
	if doc.meta.has_field("custom_weight_deduction"):
		doc.custom_weight_deduction = flt(weight_kg)
	if doc.meta.has_field("custom_bag_deduction"):
		doc.custom_bag_deduction = flt(bag_kg)
	if doc.meta.has_field("custom_weight_deduction_amount"):
		doc.custom_weight_deduction_amount = flt(weight_amt)
	if doc.meta.has_field("custom_bag_deduction_amount"):
		doc.custom_bag_deduction_amount = flt(bag_amt)


def _set_item_qty_from_deduction_kg(doc, source, deduction_kg):
	"""Return qty in quintal = deduction kg / 100, split by each source item line qty share."""
	return_qty_quintal = flt(deduction_kg) / 100
	if return_qty_quintal <= 0 or not doc.get("items"):
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

	allocations = []
	total_source_qty = 0

	for item in commodity_items:
		source_item = source_items.get(item.purchase_invoice_item)
		source_qty = flt(source_item.qty) if source_item else 0
		if source_qty > 0:
			allocations.append((item, source_qty))
			total_source_qty += source_qty

	if not allocations:
		equal_share = return_qty_quintal / len(commodity_items)
		for item in commodity_items:
			_apply_return_item_qty(doc, item, -flt(equal_share, 3))
		return

	remaining_quintal = return_qty_quintal
	for index, (item, source_qty) in enumerate(allocations):
		if index == len(allocations) - 1:
			line_quintal = remaining_quintal
		else:
			share = source_qty / total_source_qty
			line_quintal = flt(return_qty_quintal * share, 3)
			remaining_quintal = flt(remaining_quintal - line_quintal, 6)

		_apply_return_item_qty(doc, item, -flt(line_quintal, 3))


def _apply_return_item_qty(doc, item, qty):
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
