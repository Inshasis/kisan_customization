# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, get_link_to_form


def get_rental_item():
	rental_item = frappe.db.get_single_value("Kisan Master Settings", "rental_item")
	if not rental_item:
		frappe.throw(
			_("Set {0} in {1} before submitting Outward Jawak.").format(
				frappe.bold(_("Rental Item")),
				frappe.bold(_("Kisan Master Settings")),
			)
		)

	if not frappe.db.exists("Item", rental_item):
		frappe.throw(_("Rental Item {0} not found in Item master").format(rental_item))

	return rental_item


def create_sales_invoice_for_jawak(doc):
	rental_item = get_rental_item()

	item_details = frappe.db.get_value(
		"Item", rental_item, ["item_name", "stock_uom"], as_dict=True
	)

	if not doc.jawak_date:
		frappe.throw(_("Jawak Date is required before creating Sales Invoice"))

	jawak_posting_date = getdate(doc.jawak_date)
	jawak_datetime = get_datetime(doc.jawak_date)

	si = frappe.new_doc("Sales Invoice")
	si.customer = doc.storage_customer
	si.company = doc.firm
	si.set_posting_time = 1
	si.posting_date = jawak_posting_date
	si.due_date = jawak_posting_date
	if jawak_datetime:
		si.posting_time = jawak_datetime.strftime("%H:%M:%S")

	si.append(
		"items",
		{
			"item_code": rental_item,
			"item_name": item_details.item_name,
			"qty": 1,
			"rate": flt(doc.net_amount),
			"uom": item_details.stock_uom or "Nos",
			"description": _("Outward Jawak {0}").format(doc.name),
		},
	)

	si.set_missing_values()
	si.set_posting_time = 1
	si.posting_date = jawak_posting_date
	si.flags.ignore_permissions = True
	si.insert()

	if si.docstatus != 0:
		frappe.throw(_("Sales Invoice {0} must remain in Draft").format(si.name))

	doc.db_set("sales_invoice", si.name, update_modified=False)

	from kisan_customization.outward_jawak.status import update_outward_jawak_status

	update_outward_jawak_status(doc.name)

	frappe.msgprint(
		_("Created draft Sales Invoice {0}").format(get_link_to_form("Sales Invoice", si.name)),
		indicator="green",
	)


def cancel_sales_invoice_for_jawak(doc):
	if not doc.sales_invoice or not frappe.db.exists("Sales Invoice", doc.sales_invoice):
		return

	sales_invoice_name = doc.sales_invoice
	si = frappe.get_doc("Sales Invoice", sales_invoice_name)

	if si.docstatus == 2:
		doc.db_set("sales_invoice", None, update_modified=False)
		return

	# Unlink first; otherwise Frappe blocks SI delete/cancel while Outward Jawak still references it.
	doc.db_set("sales_invoice", None, update_modified=False)

	_cancel_linked_payments_for_invoice(si)

	si.reload()
	si.flags.ignore_permissions = True
	if si.docstatus == 1:
		si.cancel()
	elif si.docstatus == 0:
		si.delete()


def _cancel_linked_payments_for_invoice(sales_invoice):
	payment_entries = frappe.db.sql_list(
		"""
		SELECT DISTINCT per.parent
		FROM `tabPayment Entry Reference` per
		INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
		WHERE per.reference_doctype = 'Sales Invoice'
			AND per.reference_name = %s
			AND pe.docstatus = 1
		""",
		sales_invoice.name,
	)

	for payment_entry in payment_entries:
		pe = frappe.get_doc("Payment Entry", payment_entry)
		pe.flags.ignore_permissions = True
		pe.cancel()

	journal_entries = frappe.db.sql_list(
		"""
		SELECT DISTINCT jea.parent
		FROM `tabJournal Entry Account` jea
		INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
		WHERE jea.reference_type = 'Sales Invoice'
			AND jea.reference_name = %s
			AND je.docstatus = 1
		""",
		sales_invoice.name,
	)

	for journal_entry in journal_entries:
		je = frappe.get_doc("Journal Entry", journal_entry)
		je.flags.ignore_permissions = True
		je.cancel()
