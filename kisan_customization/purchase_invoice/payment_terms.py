# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import add_days, cint, flt, getdate


def get_payment_base_date(doc):
	return getdate(doc.posting_date or doc.bill_date or frappe.utils.today())


def apply_po_payment_terms_to_invoice(po, pi):
	"""Copy PO payment days/schedule to PI using PI posting date as base."""
	payment_days = cint(po.get("custom_payment_days"))

	if frappe.get_meta("Purchase Invoice").has_field("custom_payment_days"):
		pi.custom_payment_days = payment_days

	if po.payment_terms_template:
		pi.payment_terms_template = po.payment_terms_template

	base_date = get_payment_base_date(pi)
	grand_total = flt(pi.rounded_total) or flt(pi.grand_total)
	base_grand_total = flt(pi.base_rounded_total) or flt(pi.base_grand_total)
	po_schedule = po.get("payment_schedule") or []

	pi.set("payment_schedule", [])

	if po_schedule:
		for row in po_schedule:
			due_date = _get_schedule_due_date(base_date, payment_days, row)
			portion = flt(row.invoice_portion) or 100
			payment_amount = (grand_total * portion) / 100
			base_payment_amount = (base_grand_total * portion) / 100

			pi.append(
				"payment_schedule",
				{
					"payment_term": row.payment_term,
					"description": row.description,
					"due_date": due_date,
					"invoice_portion": portion,
					"credit_days": cint(row.credit_days) if not payment_days else payment_days,
					"payment_amount": payment_amount,
					"base_payment_amount": base_payment_amount,
					"outstanding": payment_amount,
				},
			)
	elif payment_days:
		due_date = add_days(base_date, payment_days)
		_append_single_schedule_row(pi, due_date, grand_total, base_grand_total, payment_days)
	else:
		return

	pi.due_date = _get_header_due_date(pi)


def apply_payment_days_to_invoice(doc):
	"""Recalculate PI payment schedule from PI date + custom_payment_days."""
	payment_days = cint(doc.get("custom_payment_days"))
	if not payment_days:
		return

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

	doc.due_date = _get_header_due_date(doc)


def sync_payment_terms_from_linked_po(doc):
	"""Copy PO payment terms to PI only when PI payment days are not set yet."""
	if doc.docstatus != 0:
		return

	if cint(doc.get("custom_payment_days")):
		return

	po_names = {
		row.purchase_order
		for row in doc.get("items") or []
		if row.purchase_order and frappe.db.exists("Purchase Order", row.purchase_order)
	}

	if len(po_names) != 1:
		return

	po = frappe.get_doc("Purchase Order", next(iter(po_names)))
	if not cint(po.get("custom_payment_days")) and not po.get("payment_schedule"):
		return

	apply_po_payment_terms_to_invoice(po, doc)


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
