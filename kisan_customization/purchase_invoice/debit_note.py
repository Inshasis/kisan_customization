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
	"""Draft or submitted debit note linked to PI (used to block duplicates)."""
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


def get_submitted_debit_note(purchase_invoice, exclude_name=None):
	"""Submitted debit note only (cancelled/deleted notes are ignored for UI)."""
	if not purchase_invoice:
		return None

	filters = {
		"return_against": purchase_invoice,
		"is_return": 1,
		"docstatus": 1,
	}
	if exclude_name:
		filters["name"] = ("!=", exclude_name)

	return frappe.db.get_value("Purchase Invoice", filters, "name")


@frappe.whitelist()
def get_debit_note_for_purchase_invoice(purchase_invoice):
	return get_submitted_debit_note(purchase_invoice)


@frappe.whitelist()
def has_active_debit_note(purchase_invoice):
	return bool(get_submitted_debit_note(purchase_invoice))


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


def _create_and_submit_debit_note_doc(source):
	if source.get("is_return") or not is_kisan_custom(source):
		return None

	existing = get_submitted_debit_note(source.name)
	if existing:
		return existing

	if get_active_debit_note(source.name):
		frappe.throw(
			_("A draft Debit Note already exists against this Purchase Invoice."),
			title=_("Cannot Create Debit Note"),
		)

	doc = make_debit_note(source.name)
	doc.flags.ignore_permissions = True

	previous_mute = frappe.flags.mute_messages
	frappe.flags.mute_messages = True
	try:
		doc.insert()
		doc.submit()
	finally:
		frappe.flags.mute_messages = previous_mute

	return doc.name


def auto_create_debit_note_on_pi_submit(doc, method=None):
	if doc.get("is_return") or not is_kisan_custom(doc):
		return
	if get_submitted_debit_note(doc.name):
		return
	_create_and_submit_debit_note_doc(doc)


def cancel_linked_debit_note_on_pi_cancel(doc, method=None):
	"""Cancel submitted debit note when the source Kisan Purchase Invoice is cancelled."""
	if doc.get("is_return") or not is_kisan_custom(doc):
		return

	debit_name = get_submitted_debit_note(doc.name)
	if not debit_name:
		return

	debit = frappe.get_doc("Purchase Invoice", debit_name)
	if debit.docstatus != 1:
		return

	debit.flags.ignore_permissions = True
	debit.cancel()


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

	name = _create_and_submit_debit_note_doc(source)
	return {"name": name}


def clear_kisan_debit_note_tax_withholding(doc, source=None):
	"""Debit notes from Kisan PI must keep Apply Tax Withholding Amount unchecked."""
	if not doc.get("is_return"):
		return

	if source is None:
		if not doc.get("return_against"):
			return
		source = frappe.get_doc("Purchase Invoice", doc.return_against)

	if not is_kisan_custom(source):
		return

	doc.apply_tds = 0
	if doc.meta.has_field("tax_withholding_category"):
		doc.tax_withholding_category = None
	doc.set("advance_tax", [])
	doc.set("tax_withheld_vouchers", [])

	doc.taxes = [
		row for row in doc.get("taxes") or [] if not cint(row.get("is_tax_withholding_account"))
	]


def _apply_debit_note_settings(doc, source):
	doc.is_return = 1
	doc.return_against = source.name
	doc.update_outstanding_for_self = 0
	doc.update_billed_amount_in_purchase_order = 0
	doc.update_billed_amount_in_purchase_receipt = 0

	_copy_weight_context_from_source(doc, source)

	weight_kg, bag_kg, weight_amt, bag_amt = _calculate_return_deductions(source)
	_sync_return_deduction_fields(doc, weight_kg, bag_kg, weight_amt, bag_amt)

	_set_return_item_qty_per_line(doc, source, flt(bag_kg))
	_remove_zero_qty_commodity_rows(doc)
	_merge_debit_note_commodity_rows(doc, source)

	clear_broker_commission_fields(doc)
	_clear_return_payment_term_fields(doc)
	# Quality & Other: other deduction amounts only (not bag/weight auto rows).
	sync_deduction_item_row(doc)
	_copy_stock_settings_from_source(doc, source)
	clear_kisan_debit_note_tax_withholding(doc, source=source)

	if hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def _calculate_return_deductions(source):
	"""Recalculate bag/weight kg from source PI (weight kg may be negative when gross exceeds invoice qty)."""
	weight_kg, _, weight_amt = _calculate_weight_deduction_amount(source)
	bag_kg, _, bag_amt = _calculate_bag_deduction_amount(source)
	return flt(weight_kg), flt(bag_kg), flt(weight_amt), flt(bag_amt)


def sync_kisan_debit_note_items(doc):
	"""Recompute return line qty from source PI (bag + weight net kg, split by gross share)."""
	if not doc.get("is_return") or not doc.get("return_against"):
		return

	source = frappe.get_doc("Purchase Invoice", doc.return_against)
	if not is_kisan_custom(source):
		return

	weight_kg, bag_kg, weight_amt, bag_amt = _calculate_return_deductions(source)
	_sync_return_deduction_fields(doc, weight_kg, bag_kg, weight_amt, bag_amt)
	_set_return_item_qty_per_line(doc, source, flt(bag_kg))
	_remove_zero_qty_commodity_rows(doc)
	_merge_debit_note_commodity_rows(doc, source)


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
	return flt(accepted_kg) - flt(line_gross)


def _get_debit_note_commodity_items(doc):
	deduction_item_code = get_deduction_item_code()
	return [
		item
		for item in doc.get("items") or []
		if not deduction_item_code or item.item_code != deduction_item_code
	]


def _net_return_kg_from_source(source, total_bag_kg):
	"""Net stock return kg = invoice accepted kg − arrival kg = weight deduction + bag deduction."""
	weight_kg, _, _ = _calculate_weight_deduction_amount(source)
	return max(0, flt(weight_kg) + flt(total_bag_kg))


def _set_return_item_qty_per_line(doc, source, total_bag_kg):
	"""Return qty (quintal) = net return kg split by line gross share (not per-line weight + bag)."""
	source_items = {item.name: item for item in source.get("items") or []}
	commodity_items = _get_debit_note_commodity_items(doc)
	if not commodity_items:
		return

	total_return_kg = _net_return_kg_from_source(source, total_bag_kg)
	if not total_return_kg:
		for item in commodity_items:
			_apply_return_item_qty(doc, item, 0)
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
		if not line_gross:
			_apply_return_item_qty(doc, item, 0)
			continue
		lines.append((item, line_gross))

	if not lines:
		return

	remaining_kg = total_return_kg
	for index, (item, line_gross) in enumerate(lines):
		if index == len(lines) - 1:
			return_kg = remaining_kg
		else:
			return_kg = flt(total_return_kg * line_gross / total_gross, 6)
			remaining_kg = flt(remaining_kg - return_kg, 6)

		_apply_return_item_qty(doc, item, -flt(return_kg / QUINTAL_TO_KG, 3))


def _remove_zero_qty_commodity_rows(doc):
	"""Return invoices with stock cannot keep commodity rows at qty 0."""
	deduction_item_code = get_deduction_item_code()
	keep = []
	for row in doc.get("items") or []:
		if deduction_item_code and row.item_code == deduction_item_code:
			keep.append(row)
			continue
		if flt(row.qty):
			keep.append(row)
	doc.set("items", keep)


def _source_qty_weighted_rate(source, item_code):
	"""Average rate from source PI lines (weighted by accepted qty), e.g. 10@1500 + 10@1385 → 1442.50."""
	deduction_item_code = get_deduction_item_code()
	total_qty = 0.0
	weighted_sum = 0.0
	for row in source.get("items") or []:
		if deduction_item_code and row.item_code == deduction_item_code:
			continue
		if row.item_code != item_code:
			continue
		qty = flt(row.qty)
		if qty <= 0:
			continue
		total_qty += qty
		weighted_sum += qty * flt(row.rate)
	if not total_qty:
		return 0.0
	return flt(weighted_sum / total_qty, 2)


def _apply_source_commodity_rates(doc, source):
	"""Set merged debit-note commodity rate from source PI (not gross-share return split)."""
	if not source:
		return
	conversion_rate = flt(doc.conversion_rate) or 1
	for row in _get_debit_note_commodity_items(doc):
		rate = _source_qty_weighted_rate(source, row.item_code)
		if not rate:
			continue
		row.rate = rate
		row.amount = flt(flt(row.qty) * rate, 2)
		row.base_rate = flt(rate) * conversion_rate
		row.base_amount = flt(row.amount) * conversion_rate


def _merge_debit_note_commodity_rows(doc, source=None):
	"""One debit-note row per item code; qty summed, rate from source PI qty-weighted average."""
	deduction_item_code = get_deduction_item_code()
	commodity_rows = []
	other_rows = []
	for row in doc.get("items") or []:
		if deduction_item_code and row.item_code == deduction_item_code:
			other_rows.append(row)
		else:
			commodity_rows.append(row)

	if len(commodity_rows) <= 1:
		doc.set("items", commodity_rows + other_rows)
		_apply_source_commodity_rates(doc, source)
		return

	child_meta = frappe.get_meta(commodity_rows[0].doctype)
	has_line_gross = child_meta.has_field("custom_gross_weight_kg")

	merged_rows = []
	seen_order = []
	groups = {}
	for row in commodity_rows:
		code = row.item_code
		if code not in groups:
			groups[code] = []
			seen_order.append(code)
		groups[code].append(row)

	for code in seen_order:
		rows = groups[code]
		if len(rows) == 1:
			merged_rows.append(rows[0])
			continue

		primary = rows[0]
		total_qty = sum(flt(r.qty) for r in rows)
		total_stock_qty = sum(flt(r.stock_qty) for r in rows)

		primary.qty = total_qty
		primary.received_qty = total_qty
		primary.stock_qty = total_stock_qty

		if has_line_gross:
			primary.custom_gross_weight_kg = sum(
				flt(r.get("custom_gross_weight_kg")) for r in rows
			)

		merged_rows.append(primary)

	doc.set("items", merged_rows + other_rows)
	_apply_source_commodity_rates(doc, source)


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
