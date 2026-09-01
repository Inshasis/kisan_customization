# Copyright (c) 2026, Hidayatali and contributors

import frappe


def on_trash(doc, method=None):
	_unlink_from_aggregator_booking(doc)

	if frappe.flags.get("in_aggregator_booking_cancel"):
		return

	_cancel_linked_aggregator_booking(doc)


def _unlink_from_aggregator_booking(doc):
	if not doc.name or not frappe.db.exists("DocType", "Aggregator Booking Purchase Invoice"):
		return

	frappe.db.delete(
		"Aggregator Booking Purchase Invoice",
		{"purchase_invoice": doc.name},
	)


def _cancel_linked_aggregator_booking(doc):
	booking_name = doc.get("custom_aggregator_booking")
	if not booking_name or not frappe.db.exists("Aggregator Booking", booking_name):
		return

	if frappe.db.get_value("Aggregator Booking", booking_name, "docstatus") != 1:
		return

	frappe.flags.in_aggregator_booking_cancel = True
	try:
		booking = frappe.get_doc("Aggregator Booking", booking_name)
		booking.flags.ignore_permissions = True
		booking.cancel()
	except Exception:
		frappe.log_error(title="Cancel Aggregator Booking on PI Delete")
		raise
	finally:
		frappe.flags.in_aggregator_booking_cancel = False
