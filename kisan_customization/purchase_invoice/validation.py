# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt


def validate_supplier_invoice_amount(doc):
	if not doc.meta.has_field("custom_supplier_invoice_amount") or doc.get("is_return"):
		return

	supplier_amount = flt(doc.custom_supplier_invoice_amount)
	if supplier_amount <= 0:
		frappe.throw(_("Supplier Invoice Amount must be greater than 0."))

	grand_total = flt(doc.base_grand_total) or flt(doc.grand_total) or flt(doc.rounded_total)
	if grand_total > supplier_amount:
		frappe.throw(
			_("Grand Total ({0}) cannot be greater than Supplier Invoice Amount ({1}).").format(
				frappe.format(grand_total, {"fieldtype": "Currency"}),
				frappe.format(supplier_amount, {"fieldtype": "Currency"}),
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
