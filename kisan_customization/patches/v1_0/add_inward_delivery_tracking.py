# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import cint

from kisan_customization.inward_aawak.delivery import (
	STATUS_FULLY_DELIVERED,
	STATUS_PARTIALLY_DELIVERED,
	STATUS_SUBMITTED,
	update_inward_delivery_status,
)


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabInward Aawak`
		SET status = %s
		WHERE docstatus = 1 AND (status IS NULL OR status IN ('Draft', 'Active', ''))
		""",
		STATUS_SUBMITTED,
	)

	frappe.db.sql(
		"""
		UPDATE `tabInward Aawak`
		SET status = %s
		WHERE status = 'Completed'
		""",
		STATUS_FULLY_DELIVERED,
	)

	for inward_name in frappe.get_all("Inward Aawak", filters={"docstatus": 1}, pluck="name"):
		update_inward_delivery_status(inward_name)

		inward = frappe.db.get_value(
			"Inward Aawak",
			inward_name,
			["total_bags", "released_bags", "remaining_bags"],
			as_dict=True,
		)
		if cint(inward.remaining_bags) == 0 and cint(inward.total_bags) > 0:
			frappe.db.set_value(
				"Inward Aawak",
				inward_name,
				"status",
				STATUS_FULLY_DELIVERED,
				update_modified=False,
			)
		elif cint(inward.released_bags) > 0:
			frappe.db.set_value(
				"Inward Aawak",
				inward_name,
				"status",
				STATUS_PARTIALLY_DELIVERED,
				update_modified=False,
			)

	for row in frappe.get_all(
		"Outward Jawak",
		filters={"inward_aawak": ("is", "not set")},
		fields=["name", "firm", "inward_lot_no"],
	):
		if not row.firm or not row.inward_lot_no:
			continue

		inward_name = frappe.db.get_value(
			"Inward Aawak",
			{"firm": row.firm, "lot_number": row.inward_lot_no, "docstatus": 1},
			"name",
		)
		if inward_name:
			frappe.db.set_value("Outward Jawak", row.name, "inward_aawak", inward_name, update_modified=False)

	frappe.clear_cache(doctype="Inward Aawak")
	frappe.clear_cache(doctype="Outward Jawak")
