# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

from kisan_customization.aggregator_booking.discount import apply_booking_discount_to_pi
from kisan_customization.aggregator_booking.terms import (
	apply_booking_terms_to_pi,
	persist_pi_booking_terms,
)
from kisan_customization.purchase_invoice.validation import remove_template_tax_deductions


def create_purchase_invoices_for_booking(doc):
	supplier_rows = _group_items_by_supplier(doc)
	pi_rows = []

	for supplier, rows in supplier_rows.items():
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = doc.company
		pi.posting_date = doc.booking_date
		pi.bill_date = doc.booking_date
		pi.set_posting_time = 1
		pi.flags.ignore_default_payment_terms_template = True

		if frappe.db.has_column("Purchase Invoice", "custom_aggregator_booking"):
			pi.custom_aggregator_booking = doc.name

		for row in rows:
			qty = flt(row.qty)
			pi.append(
				"items",
				{
					"item_code": row.item_code,
					"item_name": row.item_name,
					"qty": qty,
					"received_qty": qty,
					"rate": flt(row.rate),
					"uom": row.uom,
				},
			)

		pi.set_missing_values()
		apply_booking_discount_to_pi(pi, doc)
		_finalize_booking_purchase_invoice(pi, doc, supplier)
		pi.flags.ignore_permissions = True
		pi.insert()

		persist_pi_booking_terms(pi.name, doc)

		pi = frappe.get_doc("Purchase Invoice", pi.name)
		apply_booking_terms_to_pi(pi, doc)
		apply_booking_discount_to_pi(pi, doc)
		_finalize_booking_purchase_invoice(pi, doc, supplier)
		pi.flags.ignore_permissions = True
		pi.save()

		persist_pi_booking_terms(pi.name, doc)

		pi_rows.append(
			{
				"supplier": supplier,
				"purchase_invoice": pi.name,
				"grand_total": pi.grand_total,
			}
		)

	_link_purchase_invoices(doc.name, pi_rows)

	frappe.msgprint(
		_("Created {0} draft Purchase Invoice(s)").format(len(pi_rows)),
		indicator="green",
	)


def _link_purchase_invoices(docname, pi_rows):
	frappe.db.delete("Aggregator Booking Purchase Invoice", {"parent": docname})

	for idx, row in enumerate(pi_rows, start=1):
		frappe.get_doc(
			{
				"doctype": "Aggregator Booking Purchase Invoice",
				"parent": docname,
				"parenttype": "Aggregator Booking",
				"parentfield": "purchase_invoices",
				"idx": idx,
				"supplier": row["supplier"],
				"purchase_invoice": row["purchase_invoice"],
				"grand_total": row["grand_total"],
			}
		).insert(ignore_permissions=True)


def cancel_purchase_invoices_for_booking(doc):
	pi_names = _get_linked_purchase_invoices(doc)

	frappe.flags.in_aggregator_booking_cancel = True
	try:
		for pi_name in pi_names:
			if not frappe.db.exists("Purchase Invoice", pi_name):
				continue

			frappe.db.delete(
				"Aggregator Booking Purchase Invoice",
				{"parent": doc.name, "purchase_invoice": pi_name},
			)

			pi = frappe.get_doc("Purchase Invoice", pi_name)
			if pi.docstatus == 2:
				continue

			if pi.docstatus == 1:
				pi.flags.ignore_permissions = True
				pi.cancel()
			elif pi.docstatus == 0:
				pi.flags.ignore_permissions = True
				pi.delete()

		frappe.db.delete("Aggregator Booking Purchase Invoice", {"parent": doc.name})
	finally:
		frappe.flags.in_aggregator_booking_cancel = False


def cancel_legacy_purchase_orders_for_booking(doc):
	"""Cancel POs created by the old booking flow."""
	if not frappe.db.has_column("Purchase Order", "custom_aggregator_booking"):
		return

	po_names = frappe.get_all(
		"Purchase Order",
		filters={"custom_aggregator_booking": doc.name},
		pluck="name",
	)

	for po_name in po_names:
		if not frappe.db.exists("Purchase Order", po_name):
			continue

		po = frappe.get_doc("Purchase Order", po_name)
		if po.docstatus == 2:
			continue

		if po.docstatus == 1:
			linked_invoices = frappe.get_all(
				"Purchase Invoice Item",
				filters={"purchase_order": po.name, "docstatus": 1},
				pluck="parent",
				limit=1,
			)
			if linked_invoices:
				frappe.throw(
					_("Cannot cancel booking because Purchase Order {0} is already billed").format(
						get_link_to_form("Purchase Order", po.name)
					)
				)

			po.flags.ignore_permissions = True
			po.cancel()
		elif po.docstatus == 0:
			po.flags.ignore_permissions = True
			po.delete()


def _get_linked_purchase_invoices(doc):
	pi_names = []

	for row in doc.get("purchase_invoices") or []:
		if row.purchase_invoice:
			pi_names.append(row.purchase_invoice)

	if pi_names:
		return pi_names

	if frappe.db.has_column("Purchase Invoice", "custom_aggregator_booking"):
		return frappe.get_all(
			"Purchase Invoice",
			filters={"custom_aggregator_booking": doc.name},
			pluck="name",
		)

	return []


def _group_items_by_supplier(doc):
	supplier_rows = {}
	for row in doc.items:
		supplier_rows.setdefault(row.supplier, []).append(row)
	return supplier_rows


def _finalize_booking_purchase_invoice(pi, booking, supplier):
	_apply_farmer_bill_details(pi, booking, supplier)
	_set_supplier_invoice_amount(pi, booking, supplier)
	remove_template_tax_deductions(pi)
	_sync_item_received_qty(pi)


def _apply_farmer_bill_details(pi, booking, supplier):
	"""Farmers usually do not issue GST invoices; use booking reference as Bill No."""
	if not pi.bill_date:
		pi.bill_date = booking.booking_date

	if not pi.bill_no:
		pi.bill_no = _get_booking_bill_no(booking.name, supplier)


def _get_booking_bill_no(booking_name, supplier):
	bill_no = f"{booking_name}-{supplier}"
	return bill_no[:140]


def _set_supplier_invoice_amount(pi, booking, supplier):
	if not pi.meta.has_field("custom_supplier_invoice_amount"):
		return

	pi.custom_supplier_invoice_amount = _get_supplier_booking_amount(booking, supplier)


def _get_supplier_booking_amount(booking, supplier):
	total = 0
	for row in booking.get("items") or []:
		if row.supplier == supplier:
			total += flt(row.qty) * flt(row.rate)
	return total


def _sync_item_received_qty(pi):
	for row in pi.get("items") or []:
		row.received_qty = flt(row.qty)
