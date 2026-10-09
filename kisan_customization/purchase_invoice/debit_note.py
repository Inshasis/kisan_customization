# Copyright (c) 2026, Hidayatali and contributors

import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
	make_debit_note as erpnext_make_debit_note,
)
from frappe import _
from frappe.utils import cint, flt

from kisan_customization.broker_commission.service import clear_broker_commission_fields
from kisan_customization.purchase_invoice.deductions import (
	_calculate_bag_deduction_amount,
	_calculate_weight_deduction_amount,
	get_deduction_item_code,
	sync_deduction_item_row,
)
from kisan_customization.utils.deduction_utils import get_pi_total_gross_weight
from kisan_customization.utils.transaction_mode import is_kisan_custom

QUINTAL_TO_KG = 100

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


@frappe.whitelist()
def create_and_submit_debit_note(purchase_invoice):
	"""Create Kisan debit note from a submitted PI and submit (no form / outstanding prompt)."""
	frappe.has_permission("Purchase Invoice", "create", throw=True)
	frappe.has_permission("Purchase Invoice", "submit", throw=True)

	source = frappe.get_doc("Purchase Invoice", purchase_invoice)
	if source.docstatus != 1:
		frappe.throw(_("Purchase Invoice must be submitted."), title=_("Cannot Create Debit Note"))
	if source.get("is_return"):
		frappe.throw(_("Cannot create a Debit Note from a return invoice."))
	if not is_kisan_custom(source):
		frappe.throw(_("Debit Note can only be created for Kisan Custom Purchase Invoices."))

	doc = make_debit_note(purchase_invoice)
	doc.flags.ignore_permissions = True

	previous_mute = frappe.flags.mute_messages
	frappe.flags.mute_messages = True
	try:
		doc.insert()
		doc.submit()
	finally:
		frappe.flags.mute_messages = previous_mute

	return {"name": doc.name}


def _apply_debit_note_settings(doc, source):
	doc.is_return = 1
	doc.return_against = source.name
	doc.update_outstanding_for_self = 0
	doc.update_billed_amount_in_purchase_order = 0
	doc.update_billed_amount_in_purchase_receipt = 0

	_copy_weight_context_from_source(doc, source)

	weight_kg, bag_kg, weight_amt, bag_amt = _calculate_return_deductions(source)
	_sync_return_deduction_fields(doc, weight_kg, bag_kg, weight_amt, bag_amt)

	# Per item: weight deduction (accepted kg − line gross) + bag deduction (total split by gross %).
	_set_return_item_qty_per_line(doc, source, flt(bag_kg))

	clear_broker_commission_fields(doc)
	_clear_return_payment_term_fields(doc)
	# Quality & Other: other deduction amounts only (not bag/weight auto rows).
	sync_deduction_item_row(doc)
	_copy_stock_settings_from_source(doc, source)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def _calculate_return_deductions(source):
	"""Always recalculate from source PI (total qty × 100 − gross weight, bag gross − arrival)."""
	weight_kg, _, weight_amt = _calculate_weight_deduction_amount(source)
	bag_kg, _, bag_amt = _calculate_bag_deduction_amount(source)
	return flt(weight_kg), flt(bag_kg), flt(weight_amt), flt(bag_amt)


def _clear_return_payment_term_fields(doc):
	"""Debit notes must not auto-build payment_schedule from custom_payment_days on load."""
	for fieldname in ("custom_payment_days", "custom_delivery_days"):
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, None)


def _copy_weight_context_from_source(doc, source):
	for fieldname in WEIGHT_CONTEXT_FIELDS:
		if not doc.meta.has_field(fieldname):
			continue
		if source.get(fieldname) is not None:
			doc.set(fieldname, source.get(fieldname))


def _copy_stock_settings_from_source(doc, source):
	"""When PI updated stock, carry update_stock + warehouse to the debit note."""
	if not cint(source.get("update_stock")):
		return

	doc.update_stock = 1

	set_warehouse = source.get("set_warehouse")
	if set_warehouse and doc.meta.has_field("set_warehouse"):
		doc.set_warehouse = set_warehouse

	source_items = {row.name: row for row in source.get("items") or []}
	for row in doc.get("items") or []:
		source_item = source_items.get(row.get("purchase_invoice_item"))
		warehouse = None
		if source_item and source_item.get("warehouse"):
			warehouse = source_item.warehouse
		elif set_warehouse:
			warehouse = set_warehouse
		if warehouse:
			row.warehouse = warehouse


def _sync_return_deduction_fields(doc, weight_kg, bag_kg, weight_amt=0, bag_amt=0):
	if doc.meta.has_field("custom_weight_deduction"):
		doc.custom_weight_deduction = flt(weight_kg)
	if doc.meta.has_field("custom_bag_deduction"):
		doc.custom_bag_deduction = flt(bag_kg)
	if doc.meta.has_field("custom_weight_deduction_amount"):
		doc.custom_weight_deduction_amount = flt(weight_amt)
	if doc.meta.has_field("custom_bag_deduction_amount"):
		doc.custom_bag_deduction_amount = flt(bag_amt)


def _item_accepted_qty_kg(source_item):
	return flt(source_item.qty) * QUINTAL_TO_KG


def _item_line_gross_kg(source_item):
	gross = flt(source_item.get("custom_gross_weight_kg"))
	if gross > 0:
		return gross
	return _item_accepted_qty_kg(source_item)


def _calculate_item_weight_deduction_kg(source_item):
	accepted_kg = _item_accepted_qty_kg(source_item)
	line_gross = _item_line_gross_kg(source_item)
	return max(0, flt(accepted_kg) - flt(line_gross))


def _get_debit_note_commodity_items(doc):
	deduction_item_code = get_deduction_item_code()
	return [
		item
		for item in doc.get("items") or []
		if not deduction_item_code or item.item_code != deduction_item_code
	]


def _set_return_item_qty_per_line(doc, source, total_bag_kg):
	"""Item return qty (quintal) = (line weight deduction + bag share) / 100."""
	source_items = {item.name: item for item in source.get("items") or []}
	commodity_items = _get_debit_note_commodity_items(doc)
	if not commodity_items:
		return

	total_gross = flt(get_pi_total_gross_weight(source))
	if not total_gross:
		total_gross = sum(
			_item_line_gross_kg(source_items[item.purchase_invoice_item])
			for item in commodity_items
			if source_items.get(item.purchase_invoice_item)
		)

	lines = []
	for item in commodity_items:
		source_item = source_items.get(item.purchase_invoice_item)
		if not source_item:
			continue
		line_gross = _item_line_gross_kg(source_item)
		weight_ded_kg = _calculate_item_weight_deduction_kg(source_item)
		lines.append((item, line_gross, weight_ded_kg))

	if not lines:
		return

	remaining_bag_kg = flt(total_bag_kg)
	for index, (item, line_gross, weight_ded_kg) in enumerate(lines):
		if total_bag_kg and total_gross and line_gross:
			if index == len(lines) - 1:
				bag_ded_kg = remaining_bag_kg
			else:
				bag_ded_kg = flt(total_bag_kg * line_gross / total_gross, 6)
				remaining_bag_kg = flt(remaining_bag_kg - bag_ded_kg, 6)
		else:
			bag_ded_kg = 0

		return_kg = flt(weight_ded_kg) + flt(bag_ded_kg)
		if return_kg <= 0:
			_apply_return_item_qty(doc, item, 0)
			continue

		_apply_return_item_qty(doc, item, -flt(return_kg / QUINTAL_TO_KG, 3))


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
