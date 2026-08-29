# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import add_days, cint, flt, getdate

ORDER_LINK_FIELD = {
	"Purchase Order": "purchase_order",
	"Sales Order": "sales_order",
}

BROKER_FIELDS = (
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
	"custom_broker_commission_amount",
)


def get_payment_base_date(doc):
	return getdate(doc.posting_date or doc.bill_date or frappe.utils.today())


def copy_broker_fields(source, target):
	for fieldname in BROKER_FIELDS:
		if source.meta.has_field(fieldname) and target.meta.has_field(fieldname):
			target.set(fieldname, source.get(fieldname))


def apply_delivery_days_to_invoice(doc):
	delivery_days = cint(doc.get("custom_delivery_days"))
	if not delivery_days or not doc.meta.has_field("custom_delivery_date"):
		return

	doc.custom_delivery_date = add_days(get_payment_base_date(doc), delivery_days)


def apply_order_payment_terms_to_invoice(order, invoice):
	"""Copy order delivery/payment terms to invoice using invoice posting date as base."""
	payment_days = cint(order.get("custom_payment_days"))
	delivery_days = cint(order.get("custom_delivery_days"))

	if invoice.meta.has_field("custom_payment_days"):
		invoice.custom_payment_days = payment_days or None
	if invoice.meta.has_field("custom_delivery_days"):
		invoice.custom_delivery_days = delivery_days or None

	if delivery_days:
		apply_delivery_days_to_invoice(invoice)

	if order.payment_terms_template and not invoice.payment_terms_template:
		invoice.payment_terms_template = order.payment_terms_template

	base_date = get_payment_base_date(invoice)
	grand_total = flt(invoice.rounded_total) or flt(invoice.grand_total)
	base_grand_total = flt(invoice.base_rounded_total) or flt(invoice.base_grand_total)
	order_schedule = order.get("payment_schedule") or []

	invoice.set("payment_schedule", [])

	if order_schedule:
		for row in order_schedule:
			due_date = _get_schedule_due_date(base_date, payment_days, row)
			portion = flt(row.invoice_portion) or 100
			payment_amount = (grand_total * portion) / 100
			base_payment_amount = (base_grand_total * portion) / 100

			schedule_row = {
				"payment_term": row.payment_term,
				"description": row.description,
				"due_date": due_date,
				"invoice_portion": portion,
				"credit_days": cint(row.credit_days) if not payment_days else payment_days,
				"payment_amount": payment_amount,
				"base_payment_amount": base_payment_amount,
				"outstanding": payment_amount,
			}
			invoice.append("payment_schedule", schedule_row)
	elif payment_days:
		due_date = add_days(base_date, payment_days)
		_append_single_schedule_row(invoice, due_date, grand_total, base_grand_total, payment_days)
	else:
		return

	if invoice.meta.has_field("due_date"):
		invoice.due_date = _get_header_due_date(invoice)


def apply_po_payment_terms_to_invoice(po, pi):
	apply_order_payment_terms_to_invoice(po, pi)


def apply_so_payment_terms_to_invoice(so, si):
	apply_order_payment_terms_to_invoice(so, si)


def apply_payment_days_to_invoice(doc):
	"""Recalculate invoice payment schedule from posting date + custom_payment_days."""
	payment_days = cint(doc.get("custom_payment_days"))
	if payment_days:
		base_date = get_payment_base_date(doc)
		due_date = add_days(base_date, payment_days)
		grand_total = flt(doc.rounded_total) or flt(doc.grand_total)
		base_grand_total = flt(doc.base_rounded_total) or flt(doc.base_grand_total)

		schedule = doc.get("payment_schedule") or []
		if not schedule:
			_append_single_schedule_row(doc, due_date, grand_total, base_grand_total, payment_days)
		else:
			for row in schedule:
				row_due_days = payment_days or cint(row.credit_days) or 0
				row.due_date = add_days(base_date, row_due_days) if row_due_days else base_date
				if payment_days and frappe.get_meta("Payment Schedule").has_field("credit_days"):
					row.credit_days = payment_days
				portion = flt(row.invoice_portion) or 100
				row.payment_amount = (grand_total * portion) / 100
				row.base_payment_amount = (base_grand_total * portion) / 100
				row.outstanding = row.payment_amount

		if doc.meta.has_field("due_date"):
			doc.due_date = _get_header_due_date(doc)

	apply_delivery_days_to_invoice(doc)


def sync_payment_terms_from_linked_order(doc, order_doctype):
	if doc.docstatus != 0:
		return

	link_field = ORDER_LINK_FIELD.get(order_doctype)
	if not link_field:
		return

	order_names = {
		row.get(link_field)
		for row in doc.get("items") or []
		if row.get(link_field) and frappe.db.exists(order_doctype, row.get(link_field))
	}

	if len(order_names) != 1:
		return

	order = frappe.get_doc(order_doctype, next(iter(order_names)))

	if not doc.get("custom_broker"):
		copy_broker_fields(order, doc)

	if cint(doc.get("custom_payment_days")):
		return

	if (
		cint(order.get("custom_payment_days"))
		or order.get("payment_schedule")
		or cint(order.get("custom_delivery_days"))
	):
		apply_order_payment_terms_to_invoice(order, doc)


def sync_payment_terms_from_linked_po(doc):
	sync_payment_terms_from_linked_order(doc, "Purchase Order")


def sync_payment_terms_from_linked_so(doc):
	sync_payment_terms_from_linked_order(doc, "Sales Order")


def _get_schedule_due_date(base_date, payment_days, row):
	if payment_days:
		return add_days(base_date, payment_days)

	credit_days = cint(row.credit_days) or 0
	return add_days(base_date, credit_days) if credit_days else base_date


def _append_single_schedule_row(doc, due_date, grand_total, base_grand_total, payment_days=0):
	row = {
		"due_date": due_date,
		"invoice_portion": 100,
		"payment_amount": grand_total,
		"base_payment_amount": base_grand_total,
		"outstanding": grand_total,
	}
	if payment_days and frappe.get_meta("Payment Schedule").has_field("credit_days"):
		row["credit_days"] = payment_days

	doc.append("payment_schedule", row)


def _get_header_due_date(doc):
	schedule = doc.get("payment_schedule") or []
	if not schedule:
		return get_payment_base_date(doc)

	return max(getdate(row.due_date) for row in schedule if row.due_date)
