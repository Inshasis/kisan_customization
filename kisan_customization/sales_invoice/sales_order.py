# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.payment_terms import apply_so_payment_terms_to_invoice, copy_broker_fields
from kisan_customization.utils.transaction_mode import (
	MODE_FIELD,
	copy_transaction_mode,
	is_kisan_custom,
)

_KISAN_BROKER_TERM_FIELDS = (
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
	"custom_broker_commission_amount",
	"custom_payment_days",
	"custom_delivery_days",
	"custom_delivery_date",
)


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, args=None):
	"""Map Sales Order to Sales Invoice and apply custom payment/broker terms."""
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as erpnext_make_sales_invoice

	so = frappe.get_doc("Sales Order", source_name)
	doc = erpnext_make_sales_invoice(source_name, target_doc=target_doc, args=args)
	copy_transaction_mode(so, doc)

	if doc.meta.has_field(MODE_FIELD):
		doc.set(MODE_FIELD, so.get(MODE_FIELD) or doc.get(MODE_FIELD))

	if is_kisan_custom(doc):
		copy_broker_fields(so, doc)
		apply_so_payment_terms_to_invoice(so, doc)
	else:
		for fieldname in _KISAN_BROKER_TERM_FIELDS:
			if doc.meta.has_field(fieldname):
				doc.set(fieldname, None)

	return doc
