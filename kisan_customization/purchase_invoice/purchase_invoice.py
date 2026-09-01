# Copyright (c) 2026, Hidayatali and contributors

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
from kisan_customization.purchase_invoice.sauda_qty import validate_sauda_qty_range
from kisan_customization.purchase_invoice.validation import (
	clear_booking_purchase_invoice_taxes,
	remove_kisan_deduction_taxes,
	validate_supplier_invoice_amount,
)


def validate(doc, method=None):
	if not doc.get("is_return"):
		validate_supplier_invoice_amount(doc)
		validate_bag_details(doc)
		recalculate_bag_weights(doc)
		recalculate_existing_deductions(doc)
		validate_sauda_qty_range(doc)
	else:
		recalculate_bag_weights(doc)
		remove_deduction_item_rows(doc)

	if doc.get("is_return"):
		sync_deduction_item_row(doc)
	remove_kisan_deduction_taxes(doc)
	clear_booking_purchase_invoice_taxes(doc)
	sync_payment_terms_from_linked_po(doc)
	apply_payment_days_to_invoice(doc)
