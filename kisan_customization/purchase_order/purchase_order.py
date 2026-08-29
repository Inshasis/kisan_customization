# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.payment_terms import apply_po_payment_terms_to_invoice, copy_broker_fields


@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice

	doc = get_mapped_purchase_invoice(source_name, target_doc, args=args)
	po = frappe.get_doc("Purchase Order", source_name)
	copy_broker_fields(po, doc)
	apply_po_payment_terms_to_invoice(po, doc)
	return doc
