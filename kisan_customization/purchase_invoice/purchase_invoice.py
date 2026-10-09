# Copyright (c) 2026, Hidayatali and contributors

import frappe

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
	validate_unique_debit_note,
)
from kisan_customization.purchase_invoice.validation import (
	clear_booking_purchase_invoice_taxes,
	remove_kisan_deduction_taxes,
	validate_supplier_invoice_amount,
)
from kisan_customization.utils.transaction_mode import is_kisan_custom


def before_submit(doc, method=None):
	"""Kisan debit notes must not use Update Outstanding for Self (ERPNext default warning)."""
	if not doc.get("is_return") or not doc.get("return_against"):
		return

	source = frappe.get_doc("Purchase Invoice", doc.return_against)
	if is_kisan_custom(source):
		doc.update_outstanding_for_self = 0


def validate(doc, method=None):
	if doc.get("is_return"):
		clear_kisan_debit_note_tax_withholding(doc)
		recalculate_bag_weights(doc)
		remove_deduction_item_rows(doc)
		validate_unique_debit_note(doc)
		sync_deduction_item_row(doc)
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
