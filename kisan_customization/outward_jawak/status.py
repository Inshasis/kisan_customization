# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import cint, flt

STATUS_DRAFT = "Draft"
STATUS_SUBMITTED = "Submitted"
STATUS_UNPAID = "Unpaid"
STATUS_PARTIALLY_PAID = "Partially Paid"
STATUS_PAID = "Paid"
STATUS_CANCELLED = "Cancelled"

JAWAK_STATUSES = (
	STATUS_DRAFT,
	STATUS_SUBMITTED,
	STATUS_UNPAID,
	STATUS_PARTIALLY_PAID,
	STATUS_PAID,
	STATUS_CANCELLED,
)


def get_sales_invoice_total(sales_invoice, si_doc=None):
	if si_doc:
		if cint(si_doc.disable_rounded_total):
			return flt(si_doc.grand_total)
		return flt(si_doc.rounded_total or si_doc.grand_total)

	if not sales_invoice:
		return 0

	si = frappe.db.get_value(
		"Sales Invoice",
		sales_invoice,
		["grand_total", "rounded_total", "disable_rounded_total"],
		as_dict=True,
	)
	if not si:
		return 0

	if cint(si.disable_rounded_total):
		return flt(si.grand_total)

	return flt(si.rounded_total or si.grand_total)


def compute_payment_status_from_sales_invoice(si_doc):
	if not si_doc or si_doc.docstatus != 1:
		return STATUS_SUBMITTED

	outstanding = flt(si_doc.outstanding_amount)
	total = get_sales_invoice_total(si_doc.name, si_doc=si_doc)

	if total <= 0:
		return STATUS_UNPAID

	if outstanding <= 0:
		return STATUS_PAID

	if outstanding < total:
		return STATUS_PARTIALLY_PAID

	return STATUS_UNPAID


def compute_outward_jawak_status(doc, si_doc=None):
	if doc.docstatus == 2:
		return STATUS_CANCELLED

	if doc.docstatus == 0:
		return STATUS_DRAFT

	if not doc.sales_invoice:
		return STATUS_SUBMITTED

	if si_doc and si_doc.name == doc.sales_invoice:
		return compute_payment_status_from_sales_invoice(si_doc)

	if not frappe.db.exists("Sales Invoice", doc.sales_invoice):
		return STATUS_SUBMITTED

	si = frappe.db.get_value(
		"Sales Invoice",
		doc.sales_invoice,
		["docstatus", "outstanding_amount", "grand_total", "rounded_total", "disable_rounded_total"],
		as_dict=True,
	)

	if not si or si.docstatus == 0:
		return STATUS_SUBMITTED

	if si.docstatus == 2:
		return STATUS_SUBMITTED

	outstanding = flt(si.outstanding_amount)
	total = get_sales_invoice_total(doc.sales_invoice)

	if total <= 0:
		return STATUS_UNPAID

	if outstanding <= 0:
		return STATUS_PAID

	if outstanding < total:
		return STATUS_PARTIALLY_PAID

	return STATUS_UNPAID


def update_outward_jawak_status(jawak_name, si_doc=None, commit=False):
	if not jawak_name or not frappe.db.exists("Outward Jawak", jawak_name):
		return

	doc = frappe.get_doc("Outward Jawak", jawak_name)
	status = compute_outward_jawak_status(doc, si_doc=si_doc)

	if doc.status == status:
		return status

	frappe.db.set_value("Outward Jawak", jawak_name, "status", status, update_modified=False)

	if commit:
		frappe.db.commit()

	return status


def update_jawak_status_from_sales_invoice(sales_invoice, si_doc=None, commit=False):
	if not sales_invoice:
		return

	jawak_names = frappe.get_all(
		"Outward Jawak",
		filters={"sales_invoice": sales_invoice},
		pluck="name",
	)

	for jawak_name in jawak_names:
		update_outward_jawak_status(jawak_name, si_doc=si_doc, commit=commit)


def update_jawak_from_payment_entry(doc, method=None):
	for ref in doc.get("references") or []:
		if ref.reference_doctype == "Sales Invoice" and ref.reference_name:
			update_jawak_status_from_sales_invoice(ref.reference_name)


def on_sales_invoice_update(doc, method=None):
	if doc.docstatus == 0 and method not in ("on_cancel",):
		return

	update_jawak_status_from_sales_invoice(doc.name, si_doc=doc)
