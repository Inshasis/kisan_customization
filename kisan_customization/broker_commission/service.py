# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt, getdate

INVOICE_LINK_FIELD = {
	"Purchase Invoice": "purchase_invoice",
	"Sales Invoice": "sales_invoice",
}


def should_create_broker_commission(doc):
	if doc.get("is_return"):
		return False

	return doc.get("custom_broker") and flt(doc.get("custom_broker_commission_amount")) > 0


BROKER_COMMISSION_FIELDS = (
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
	"custom_broker_commission_amount",
)


def clear_broker_commission_fields(doc):
	for fieldname in BROKER_COMMISSION_FIELDS:
		if not doc.meta.has_field(fieldname):
			continue

		if fieldname in ("custom_broker", "custom_commission_type"):
			doc.set(fieldname, None)
		else:
			doc.set(fieldname, 0)


def get_invoice_link_field(doctype):
	return INVOICE_LINK_FIELD.get(doctype)


def get_broker_commission_payload(doc):
	link_field = get_invoice_link_field(doc.doctype)
	if not link_field:
		return None

	return {
		"doctype": "Broker Commission",
		link_field: doc.name,
		"posting_date": getdate(doc.posting_date),
		"company": doc.company,
		"broker": doc.custom_broker,
		"commission_type": doc.custom_commission_type,
		"commission_percent": flt(doc.custom_commission_percent),
		"commission_amount": flt(doc.custom_commission_amount),
		"broker_commission_amount": flt(doc.custom_broker_commission_amount),
	}


def create_broker_commission_on_submit(doc):
	if not should_create_broker_commission(doc):
		return

	link_field = get_invoice_link_field(doc.doctype)
	if not link_field:
		return

	if frappe.db.exists("Broker Commission", {link_field: doc.name, "docstatus": ("<", 2)}):
		return

	bc = frappe.get_doc(get_broker_commission_payload(doc))
	bc.insert(ignore_permissions=True)
	bc.flags.ignore_permissions = True
	bc.submit()


def cancel_broker_commission_on_cancel(doc):
	link_field = get_invoice_link_field(doc.doctype)
	if not link_field:
		return

	bc_names = frappe.get_all(
		"Broker Commission",
		filters={link_field: doc.name, "docstatus": 1},
		pluck="name",
	)

	for bc_name in bc_names:
		_cancel_broker_commission(bc_name)


def _cancel_broker_commission(bc_name):
	bc = frappe.get_doc("Broker Commission", bc_name)
	je_name = bc.journal_entry
	bc.flags.ignore_permissions = True
	bc.flags.ignore_links = True

	if bc.docstatus == 1:
		bc.cancel()

	# Safety net in case the journal entry is still submitted.
	_cancel_journal_entry(je_name)


def _cancel_journal_entry(je_name):
	if not je_name or not frappe.db.exists("Journal Entry", je_name):
		return

	je = frappe.get_doc("Journal Entry", je_name)
	if je.docstatus != 1:
		return

	je.flags.ignore_permissions = True
	je.cancel()
