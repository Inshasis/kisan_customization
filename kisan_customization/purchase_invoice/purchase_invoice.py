# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

from kisan_customization.purchase_invoice.bags import (
	recalculate_bag_weights,
	validate_bag_details,
)
from kisan_customization.purchase_invoice.deductions import (
	recalculate_existing_deductions,
	remove_deduction_item_rows,
	sync_deduction_item_row,
)
from kisan_customization.purchase_invoice.payment_terms import (
	apply_payment_days_to_invoice,
	sync_payment_terms_from_linked_po,
)
from kisan_customization.purchase_invoice.item_gross_weight import validate_item_gross_weights
from kisan_customization.purchase_invoice.sauda_qty import validate_sauda_qty_range
from kisan_customization.purchase_invoice.debit_note import (
	clear_kisan_debit_note_tax_withholding,
	sync_kisan_debit_note_items,
	validate_unique_debit_note,
)
from kisan_customization.purchase_invoice.validation import (
	clear_booking_purchase_invoice_taxes,
	remove_kisan_deduction_taxes,
	validate_supplier_invoice_amount,
)
from kisan_customization.utils.transaction_mode import is_kisan_custom

_REQUIRED_SUBMIT_DEDUCTIONS = frozenset({"Moise", "Damage", "S/S"})


def _deduction_type_base(name):
	return (name or "").split(" (")[0].strip()


def _validate_required_deduction_actuals(doc):
	if doc.get("is_return") or not is_kisan_custom(doc):
		return

	missing = set(_REQUIRED_SUBMIT_DEDUCTIONS)
	for row in doc.get("custom_deductions") or []:
		base = _deduction_type_base(row.get("deduction_type_name"))
		if base in missing and flt(row.get("actual")) > 0:
			missing.discard(base)

	if missing:
		frappe.throw(
			_("Before submit, enter Actual greater than 0 for: {0}").format(
				", ".join(sorted(missing))
			),
			title=_("Deduction Details Required"),
		)


def before_submit(doc, method=None):
	if doc.get("is_return") and doc.get("return_against"):
		source = frappe.get_doc("Purchase Invoice", doc.return_against)
		if is_kisan_custom(source):
			doc.update_outstanding_for_self = 0
			sync_kisan_debit_note_items(doc)
			if hasattr(doc, "calculate_taxes_and_totals"):
				doc.calculate_taxes_and_totals()
		return

	_validate_required_deduction_actuals(doc)


def validate(doc, method=None):
	if doc.get("is_return"):
		clear_kisan_debit_note_tax_withholding(doc)
		recalculate_bag_weights(doc)
		remove_deduction_item_rows(doc)
		validate_unique_debit_note(doc)
		sync_kisan_debit_note_items(doc)
		sync_deduction_item_row(doc)
		if hasattr(doc, "calculate_taxes_and_totals"):
			doc.calculate_taxes_and_totals()
	elif is_kisan_custom(doc):
		validate_bag_details(doc)
		validate_item_gross_weights(doc)
		recalculate_bag_weights(doc)
		recalculate_existing_deductions(doc)
		validate_sauda_qty_range(doc)
		remove_kisan_deduction_taxes(doc)
		clear_booking_purchase_invoice_taxes(doc)
		sync_payment_terms_from_linked_po(doc)
		apply_payment_days_to_invoice(doc)
		if hasattr(doc, "calculate_taxes_and_totals"):
			doc.calculate_taxes_and_totals()
		validate_supplier_invoice_amount(doc)
