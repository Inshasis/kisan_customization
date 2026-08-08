# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt, getdate


def on_submit(doc, method=None):
	if not _should_create_broker_commission(doc):
		return

	if frappe.db.exists(
		"Broker Commission",
		{"purchase_invoice": doc.name, "docstatus": ("<", 2)},
	):
		return

	bc = frappe.get_doc(
		{
			"doctype": "Broker Commission",
			"purchase_invoice": doc.name,
			"posting_date": getdate(doc.posting_date),
			"company": doc.company,
			"broker": doc.custom_broker,
			"commission_type": doc.custom_commission_type,
			"commission_percent": flt(doc.custom_commission_percent),
			"commission_amount": flt(doc.custom_commission_amount),
			"broker_commission_amount": flt(doc.custom_broker_commission_amount),
		}
	)
	bc.insert(ignore_permissions=True)
	bc.flags.ignore_permissions = True
	bc.submit()


def on_cancel(doc, method=None):
	bc_name = frappe.db.get_value(
		"Broker Commission",
		{"purchase_invoice": doc.name, "docstatus": 1},
		"name",
	)
	if not bc_name:
		return

	bc = frappe.get_doc("Broker Commission", bc_name)
	bc.flags.ignore_permissions = True
	bc.cancel()


def _should_create_broker_commission(doc):
	return doc.custom_broker and flt(doc.custom_broker_commission_amount) > 0
