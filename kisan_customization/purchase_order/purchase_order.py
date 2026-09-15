# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.payment_terms import apply_po_payment_terms_to_invoice, copy_broker_fields
from kisan_customization.utils.transaction_mode import (
	MODE_FIELD,
	copy_transaction_mode,
	is_kisan_custom,
)


@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice

	po = frappe.get_doc("Purchase Order", source_name)
	doc = get_mapped_purchase_invoice(source_name, target_doc, args=args)
	copy_transaction_mode(po, doc)

	if doc.meta.has_field(MODE_FIELD):
		doc.set(MODE_FIELD, po.get(MODE_FIELD) or doc.get(MODE_FIELD))

	if is_kisan_custom(doc):
		copy_broker_fields(po, doc)
		apply_po_payment_terms_to_invoice(po, doc)
	elif doc.meta.has_field(MODE_FIELD):
		for fieldname in (
			"custom_broker",
			"custom_commission_type",
			"custom_commission_percent",
			"custom_commission_amount",
			"custom_broker_commission_amount",
			"custom_payment_days",
			"custom_delivery_days",
		):
			if doc.meta.has_field(fieldname):
				doc.set(fieldname, None)

	return doc
