# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt


@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice

	doc = get_mapped_purchase_invoice(source_name, target_doc, args=args)
	po = frappe.get_doc("Purchase Order", source_name)
	apply_po_dates_to_purchase_invoice(po, doc)
	return doc


def apply_po_dates_to_purchase_invoice(po, pi):
	if po.schedule_date:
		pi.due_date = po.schedule_date

	if po.payment_terms_template:
		pi.payment_terms_template = po.payment_terms_template

	if not po.get("payment_schedule"):
		return

	grand_total = flt(pi.rounded_total) or flt(pi.grand_total)
	base_grand_total = flt(pi.base_rounded_total) or flt(pi.base_grand_total)

	pi.set("payment_schedule", [])
	for row in po.payment_schedule:
		portion = flt(row.invoice_portion) or 100
		pi.append(
			"payment_schedule",
			{
				"payment_term": row.payment_term,
				"description": row.description,
				"due_date": row.due_date,
				"invoice_portion": portion,
				"payment_amount": (grand_total * portion) / 100,
				"base_payment_amount": (base_grand_total * portion) / 100,
				"outstanding": (grand_total * portion) / 100,
			},
		)
