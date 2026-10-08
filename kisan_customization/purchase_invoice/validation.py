# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

SUPPLIER_INVOICE_AMOUNT_TOLERANCE = 1.0


def _purchase_invoice_rounded_total(doc):
	return flt(doc.get("rounded_total")) or flt(doc.get("grand_total"))


def validate_supplier_invoice_amount(doc):
	if not doc.meta.has_field("custom_supplier_invoice_amount") or doc.get("is_return"):
		return

	supplier_amount = flt(doc.custom_supplier_invoice_amount)
	if supplier_amount <= 0:
		frappe.throw(_("Supplier Invoice Amount must be greater than 0."))

	rounded_total = _purchase_invoice_rounded_total(doc)
	if abs(supplier_amount - rounded_total) > SUPPLIER_INVOICE_AMOUNT_TOLERANCE:
		frappe.throw(
			_(
				"Supplier Invoice Amount ({0}) must match Rounded Total ({1}) (allowed difference: {2})."
			).format(
				frappe.format(supplier_amount, {"fieldtype": "Currency", "currency": doc.currency}),
				frappe.format(rounded_total, {"fieldtype": "Currency", "currency": doc.currency}),
				frappe.format(
					SUPPLIER_INVOICE_AMOUNT_TOLERANCE,
					{"fieldtype": "Currency", "currency": doc.currency},
				),
			)
		)


def is_kisan_deduction_tax(tax):
	if tax.add_deduct_tax != "Deduct":
		return False

	description = tax.description or ""
	return description.startswith("Deductions:") or "|" in description


def remove_kisan_deduction_taxes(doc):
	"""Remove custom deduction rows from Purchase Taxes and Charges."""
	removed = False

	for tax in list(doc.get("taxes") or []):
		if is_kisan_deduction_tax(tax):
			doc.remove(tax)
			removed = True

	if removed and hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def remove_template_tax_deductions(doc):
	"""Remove supplier tax-template deduction rows; keep GST."""
	removed = False

	for tax in list(doc.get("taxes") or []):
		if tax.add_deduct_tax == "Deduct" and not is_kisan_deduction_tax(tax):
			doc.remove(tax)
			removed = True

	if removed and hasattr(doc, "calculate_taxes_and_totals"):
		doc.calculate_taxes_and_totals()


def clear_booking_purchase_invoice_taxes(doc):
	if not doc.get("custom_aggregator_booking"):
		return

	remove_template_tax_deductions(doc)
