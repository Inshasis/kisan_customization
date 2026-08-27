# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.exists("DocType", "Aggregator Booking Commodity"):
		return

	if not frappe.db.has_column("Aggregator Booking", "commodity"):
		return

	bookings = frappe.get_all(
		"Aggregator Booking",
		fields=["name", "commodity", "rate", "aggregator_qty"],
		filters={"commodity": ["is", "set"]},
	)

	for booking in bookings:
		if frappe.db.exists(
			"Aggregator Booking Commodity",
			{"parent": booking.name, "item_code": booking.commodity},
		):
			continue

		item_name = frappe.db.get_value("Item", booking.commodity, "item_name")
		allocated_qty = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(qty), 0)
			FROM `tabAggregator Booking Item`
			WHERE parent = %s AND item_code = %s
			""",
			(booking.name, booking.commodity),
		)[0][0]

		frappe.get_doc(
			{
				"doctype": "Aggregator Booking Commodity",
				"parent": booking.name,
				"parenttype": "Aggregator Booking",
				"parentfield": "commodities",
				"item_code": booking.commodity,
				"item_name": item_name,
				"rate": flt(booking.rate),
				"aggregator_qty": flt(booking.aggregator_qty),
				"allocated_qty": flt(allocated_qty),
				"amount": flt(booking.aggregator_qty) * flt(booking.rate),
			}
		).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Aggregator Booking")
