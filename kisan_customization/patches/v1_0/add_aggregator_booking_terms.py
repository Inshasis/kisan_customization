# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import date_diff, getdate


def execute():
	meta = frappe.get_meta("Aggregator Booking", cached=False)
	fieldnames = {field.fieldname for field in meta.fields}

	if "total_amount" in fieldnames and frappe.db.has_column("Aggregator Booking", "grand_total"):
		frappe.db.sql(
			"""
			UPDATE `tabAggregator Booking`
			SET total_amount = grand_total
			WHERE IFNULL(total_amount, 0) = 0 AND IFNULL(grand_total, 0) > 0
			"""
		)

	if "delivery_days" in fieldnames and frappe.db.has_column("Aggregator Booking", "required_by"):
		rows = frappe.get_all(
			"Aggregator Booking",
			fields=["name", "booking_date", "required_by", "delivery_days"],
		)
		for row in rows:
			updates = {}
			if not row.delivery_days and row.required_by and row.booking_date:
				days = date_diff(getdate(row.required_by), getdate(row.booking_date))
				if days > 0:
					updates["delivery_days"] = days

			if updates:
				frappe.db.set_value("Aggregator Booking", row.name, updates, update_modified=False)

	frappe.clear_cache(doctype="Aggregator Booking")
