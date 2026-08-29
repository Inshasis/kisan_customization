# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.payment_terms import apply_so_payment_terms_to_invoice, copy_broker_fields


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False, args=None):
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as erpnext_make_sales_invoice

	doc = erpnext_make_sales_invoice(source_name, target_doc, ignore_permissions, args)
	so = frappe.get_doc("Sales Order", source_name)
	copy_broker_fields(so, doc)
	apply_so_payment_terms_to_invoice(so, doc)
	return doc
