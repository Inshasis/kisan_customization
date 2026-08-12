# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_link_to_form


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

	si = frappe.new_doc("Sales Invoice")
	si.customer = doc.storage_customer
	si.company = doc.firm
	si.posting_date = getdate(doc.jawak_date)
	si.due_date = getdate(doc.jawak_date)

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
	si.flags.ignore_permissions = True
	si.insert()
	si.submit()

	doc.db_set("sales_invoice", si.name, update_modified=False)

	frappe.msgprint(
		_("Created Sales Invoice {0}").format(get_link_to_form("Sales Invoice", si.name)),
		indicator="green",
	)


def cancel_sales_invoice_for_jawak(doc):
	if not doc.sales_invoice or not frappe.db.exists("Sales Invoice", doc.sales_invoice):
		return

	si = frappe.get_doc("Sales Invoice", doc.sales_invoice)
	if si.docstatus == 2:
		return

	if si.docstatus == 1:
		if flt(si.outstanding_amount) < flt(si.grand_total):
			frappe.throw(
				_("Cannot cancel because Sales Invoice {0} has linked payments").format(
					get_link_to_form("Sales Invoice", si.name)
				)
			)

		si.flags.ignore_permissions = True
		si.cancel()
	elif si.docstatus == 0:
		si.flags.ignore_permissions = True
		si.delete()
