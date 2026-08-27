# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

from kisan_customization.aggregator_booking.discount import apply_booking_discount_to_po
from kisan_customization.aggregator_booking.terms import (
	apply_booking_terms_to_po,
	compute_delivery_date,
	persist_po_booking_terms,
)


def create_purchase_orders_for_booking(doc):
	supplier_rows = _group_items_by_supplier(doc)
	delivery_date = compute_delivery_date(doc)
	po_rows = []

	for supplier, rows in supplier_rows.items():
		po = frappe.new_doc("Purchase Order")
		po.supplier = supplier
		po.company = doc.company
		po.transaction_date = doc.booking_date

		if frappe.db.has_column("Purchase Order", "custom_aggregator_booking"):
			po.custom_aggregator_booking = doc.name

		for row in rows:
			po.append(
				"items",
				{
					"item_code": row.item_code,
					"item_name": row.item_name,
					"qty": flt(row.qty),
					"rate": flt(row.rate),
					"uom": row.uom,
					"schedule_date": delivery_date,
				},
			)

		po.set_missing_values()
		apply_booking_discount_to_po(po, doc)
		po.flags.ignore_permissions = True
		po.insert()

		persist_po_booking_terms(po.name, doc)

		po = frappe.get_doc("Purchase Order", po.name)
		apply_booking_terms_to_po(po, doc)
		apply_booking_discount_to_po(po, doc)
		po.flags.ignore_permissions = True
		po.save()

		persist_po_booking_terms(po.name, doc)

		po = frappe.get_doc("Purchase Order", po.name)
		po.flags.ignore_permissions = True
		po.flags.ignore_validate_update_after_submit = True
		po.submit()

		po_rows.append(
			{
				"supplier": supplier,
				"purchase_order": po.name,
				"grand_total": po.grand_total,
			}
		)

	_link_purchase_orders(doc.name, po_rows)

	frappe.msgprint(
		_("Created {0} Purchase Order(s)").format(len(po_rows)),
		indicator="green",
	)


def _link_purchase_orders(docname, po_rows):
	frappe.db.delete("Aggregator Booking Purchase Order", {"parent": docname})

	for idx, row in enumerate(po_rows, start=1):
		frappe.get_doc(
			{
				"doctype": "Aggregator Booking Purchase Order",
				"parent": docname,
				"parenttype": "Aggregator Booking",
				"parentfield": "purchase_orders",
				"idx": idx,
				"supplier": row["supplier"],
				"purchase_order": row["purchase_order"],
				"grand_total": row["grand_total"],
			}
		).insert(ignore_permissions=True)


def cancel_purchase_orders_for_booking(doc):
	if not doc.purchase_orders:
		return

	for row in doc.purchase_orders:
		if not row.purchase_order or not frappe.db.exists("Purchase Order", row.purchase_order):
			continue

		po = frappe.get_doc("Purchase Order", row.purchase_order)
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


def _group_items_by_supplier(doc):
	supplier_rows = {}
	for row in doc.items:
		supplier_rows.setdefault(row.supplier, []).append(row)
	return supplier_rows
